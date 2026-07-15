from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import typer

from .agent import run_agent
from .config import OUTPUT_DIR, RAW_DIR
from .database_tools import DatabaseRouter
from .skills import build_skill_registry
from .skills.base import SkillContext

app = typer.Typer(
    help="Hydride NH3 Agent command-line interface: CLI/API/Chainlit/MCP-ready scientific workflows."
)

# Rich is optional. The CLI still works in plain terminals if rich is absent.
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text
    from rich import box

    console = Console()
    RICH_AVAILABLE = True
except Exception:  # pragma: no cover
    console = None
    RICH_AVAILABLE = False


def _echo(message: Any = "") -> None:
    if RICH_AVAILABLE:
        console.print(message)
    else:
        typer.echo(str(message))


def _echo_json(obj: Any) -> None:
    if RICH_AVAILABLE:
        console.print_json(json.dumps(obj, ensure_ascii=False, default=str))
    else:
        typer.echo(json.dumps(obj, indent=2, ensure_ascii=False, default=str))


def _parse_parameters(parameters: str | None) -> dict[str, Any]:
    if not parameters:
        return {}
    try:
        parsed = json.loads(parameters)
    except json.JSONDecodeError as exc:
        raise typer.BadParameter(f"--parameters must be valid JSON: {exc}") from exc
    if not isinstance(parsed, dict):
        raise typer.BadParameter("--parameters JSON must decode to an object/dict.")
    return parsed


def _database_rows(raw_dir: Path) -> list[dict[str, Any]]:
    router = DatabaseRouter(raw_dir=raw_dir)
    rows: list[dict[str, Any]] = []
    for item in router.list_databases():
        path = router.path_for(item["key"])
        rows.append(
            {
                "key": item["key"],
                "status": "OK" if path.exists() else "MISSING",
                "path": str(path),
            }
        )
    return rows


def _render_database_table(raw_dir: Path) -> None:
    rows = _database_rows(raw_dir)
    if RICH_AVAILABLE:
        table = Table(title="Hydride NH3 Agent databases", box=box.SIMPLE_HEAVY)
        table.add_column("Database", style="bold")
        table.add_column("Status")
        table.add_column("Path", overflow="fold")
        for row in rows:
            status = "[green]OK[/green]" if row["status"] == "OK" else "[red]MISSING[/red]"
            table.add_row(row["key"], status, row["path"])
        console.print(table)
    else:
        for row in rows:
            typer.echo(f"{row['key']:<16} {row['status']:<8} {row['path']}")


def _render_skill_table() -> None:
    skills = build_skill_registry().list()
    if RICH_AVAILABLE:
        table = Table(title="Available skills", box=box.SIMPLE_HEAVY)
        table.add_column("Skill", style="bold")
        table.add_column("Databases")
        table.add_column("Figure")
        table.add_column("Table")
        table.add_column("Description", overflow="fold")
        for skill in skills:
            table.add_row(
                skill.get("name", ""),
                ", ".join(skill.get("databases", []) or ["—"]),
                "yes" if skill.get("produces_figure") else "no",
                "yes" if skill.get("produces_table") else "no",
                skill.get("description", ""),
            )
        console.print(table)
    else:
        _echo_json(skills)


@app.command("check-data")
def check_data(raw_dir: Path = RAW_DIR) -> None:
    """Check whether the configured demo/raw databases are available."""
    _render_database_table(raw_dir=raw_dir)


@app.command("check-files")
def check_files(raw_dir: Path = RAW_DIR) -> None:
    """Backward-compatible alias for the before-0630 check-files command."""
    check_data(raw_dir=raw_dir)


@app.command("list-skills")
def list_skills(format: str = typer.Option("json", "--format", "-f", help="json or table")) -> None:
    """List available agent skills."""
    if format.lower() == "table":
        _render_skill_table()
    else:
        _echo_json(build_skill_registry().list())


@app.command("front")
def front(raw_dir: Path = RAW_DIR) -> None:
    """Show a console front page for the agentic-ready package."""
    if RICH_AVAILABLE:
        title = Text("Hydride NH3 Agent — agentic-ready package", style="bold cyan")
        body = (
            "Four synchronized interfaces expose the same curated hydride/NH3 skills:\n\n"
            "CLI       : hydride-agent check-data | list-skills | run-skill | demo\n"
            "API       : /databases, /skills, /chat, /skills/{skill_name}\n"
            "Chainlit  : browser-based interactive material analysis\n"
            "MCP/Codex : list_databases, list_skills, run_skill, answer_question\n\n"
            "Scientific scope: NH3/ammine hydrides, state behavior, descriptor mapping, "
            "conductivity loading, H2 release, and coordination-mechanism synthesis."
        )
        console.print(Panel(body, title=title, border_style="cyan", expand=False))
        _render_database_table(raw_dir=raw_dir)
        _render_skill_table()

        quick = Table(title="Video-ready commands", box=box.SIMPLE_HEAVY)
        quick.add_column("Purpose", style="bold")
        quick.add_column("Command", overflow="fold")
        quick.add_row("Data reproducibility", "hydride-agent check-data")
        quick.add_row("Skill registry", "hydride-agent list-skills --format table")
        quick.add_row("Generate state figure/table", "hydride-agent run-skill state_complexity")
        quick.add_row("Run robust demo", "hydride-agent demo")
        console.print(quick)
    else:
        typer.echo("Hydride NH3 Agent — agentic-ready package")
        typer.echo("Interfaces: CLI, FastAPI, Chainlit, MCP/Codex")
        typer.echo("Commands: check-data, list-skills, run-skill, ask, demo")
        check_data(raw_dir=raw_dir)
        list_skills(format="json")


@app.command("agentic-status")
def agentic_status(raw_dir: Path = RAW_DIR) -> None:
    """Alias of 'front' for recording a package-status segment."""
    front(raw_dir=raw_dir)


@app.command("run-skill")
def run_skill(
    skill_name: str,
    parameters: str | None = typer.Option(None, "--parameters", "-p", help="JSON object passed to the skill."),
    raw_dir: Path = RAW_DIR,
    out_dir: Path = OUTPUT_DIR,
    strict: bool = typer.Option(False, "--strict", help="Raise traceback on skill failure instead of printing a clean error."),
) -> None:
    """Run a named skill directly and print generated files/evidence.

    Examples:
      hydride-agent run-skill state_complexity
      hydride-agent run-skill state_sequence_lookup -p "{\"system\":\"LiBH4\"}"
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    registry = build_skill_registry()
    skill = registry.get(skill_name)
    context = SkillContext(
        raw_dir=raw_dir,
        output_dir=out_dir,
        user_request=f"CLI run-skill {skill_name}",
        parameters=_parse_parameters(parameters),
    )

    try:
        result = skill.run(context)
    except Exception as exc:
        if strict:
            raise
        _echo(f"[red]Skill failed:[/red] {skill_name}" if RICH_AVAILABLE else f"Skill failed: {skill_name}")
        _echo(str(exc))
        raise typer.Exit(code=1) from exc

    _echo(f"[green]OK[/green] {result.message or f'Skill completed: {result.skill}'}" if RICH_AVAILABLE else (result.message or f"Skill completed: {result.skill}"))
    if result.files:
        _echo("\nGenerated files:")
        for path in result.files:
            _echo(f"- {path}")
    if result.evidence:
        _echo("\nEvidence summary:")
        _echo_json(result.evidence)


@app.command("demo")
def demo(
    raw_dir: Path = RAW_DIR,
    out_dir: Path = OUTPUT_DIR / "cli_demo",
    strict: bool = typer.Option(False, "--strict", help="Stop at first failing skill."),
    include_conductivity: bool = typer.Option(False, "--include-conductivity/--no-conductivity", help="Try conductivity_loading in the demo. It may be skipped if the demo DigBat subset has no screened records."),
) -> None:
    """Run a video-ready agentic package demo.

    The demo is robust by default: if a skill has no eligible records in the demo data,
    the CLI marks it as SKIPPED instead of crashing. Use --strict for debugging.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    if RICH_AVAILABLE:
        console.print(Panel("Hydride NH3 Agent CLI demo", subtitle="agentic-ready smoke workflow", border_style="cyan"))
    else:
        typer.echo("Hydride NH3 Agent CLI demo")

    _echo("\n[1/4] Checking databases")
    _render_database_table(raw_dir=raw_dir)

    _echo("\n[2/4] Listing skills")
    _render_skill_table() if RICH_AVAILABLE else _echo_json(build_skill_registry().list())

    demo_skills = ["state_complexity", "state_sequence_lookup"]
    if include_conductivity:
        demo_skills.append("conductivity_loading")

    registry = build_skill_registry()
    generated: list[str] = []
    evidence_index: dict[str, Any] = {}
    status_index: dict[str, Any] = {}

    total_steps = 2 + len(demo_skills)
    for offset, skill_name in enumerate(demo_skills, start=3):
        _echo(f"\n[{offset}/{total_steps}] Running {skill_name}")
        skill = registry.get(skill_name)
        context = SkillContext(
            raw_dir=raw_dir,
            output_dir=out_dir,
            user_request=f"CLI demo: {skill_name}",
            parameters={},
        )
        try:
            result = skill.run(context)
        except Exception as exc:
            status_index[skill_name] = {"status": "SKIPPED_OR_FAILED", "reason": str(exc)}
            _echo(f"[yellow]SKIPPED[/yellow] {skill_name}: {exc}" if RICH_AVAILABLE else f"SKIPPED {skill_name}: {exc}")
            if strict:
                raise
            continue

        _echo(f"[green]OK[/green] {result.message or f'Completed {skill_name}'}" if RICH_AVAILABLE else (result.message or f"Completed {skill_name}"))
        generated.extend(str(path) for path in result.files)
        evidence_index[skill_name] = result.evidence
        status_index[skill_name] = {"status": "OK", "files": [str(path) for path in result.files]}

    report = {
        "demo": "hydride-agent demo",
        "interfaces": ["CLI", "FastAPI", "Chainlit", "MCP/Codex"],
        "skills_requested": demo_skills,
        "skill_status": status_index,
        "generated_files": generated,
        "evidence_keys": {k: list(v.keys()) if isinstance(v, dict) else [] for k, v in evidence_index.items()},
    }
    report_path = out_dir / "demo_manifest.json"
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False, default=str), encoding="utf-8")

    _echo(f"\nDone. Demo manifest: {report_path}")
    if generated:
        _echo("Generated files:")
        for path in generated:
            _echo(f"- {path}")


@app.command("ask")
def ask(
    question: str,
    raw_dir: Path = RAW_DIR,
    out_dir: Path = OUTPUT_DIR,
    session_id: str = "cli-session",
) -> None:
    """Ask the tool-gated agent a natural-language question."""
    result = run_agent(question, session_id=session_id, raw_dir=raw_dir, out_dir=out_dir)
    typer.echo(result.answer)
    if result.files:
        typer.echo("\nGenerated files:")
        for path in result.files:
            typer.echo(f"- {path}")


if __name__ == "__main__":
    app()
