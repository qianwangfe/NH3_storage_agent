from __future__ import annotations

import json
from pathlib import Path

import typer

from .agent import run_agent
from .config import OUTPUT_DIR, RAW_DIR
from .database_tools import DatabaseRouter
from .skills import build_skill_registry

app = typer.Typer(help="NH3 Storage Agent command-line interface.")


@app.command("check-data")
def check_data(raw_dir: Path = RAW_DIR) -> None:
    router = DatabaseRouter(raw_dir=raw_dir)
    for item in router.list_databases():
        path = router.path_for(item["key"])
        status = "OK" if path.exists() else "MISSING"
        typer.echo(f"{item['key']:<16} {status:<8} {path}")


@app.command("list-skills")
def list_skills() -> None:
    typer.echo(json.dumps(build_skill_registry().list(), indent=2, ensure_ascii=False))


@app.command("ask")
def ask(
    question: str,
    raw_dir: Path = RAW_DIR,
    out_dir: Path = OUTPUT_DIR,
    session_id: str = "cli-session",
) -> None:
    result = run_agent(question, session_id=session_id, raw_dir=raw_dir, out_dir=out_dir)
    typer.echo(result.answer)
    if result.files:
        typer.echo("\nGenerated files:")
        for path in result.files:
            typer.echo(f"- {path}")


if __name__ == "__main__":
    app()
