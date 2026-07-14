from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from threading import Lock
from typing import Any

from .config import OUTPUT_DIR, RAW_DIR
from .database_tools import DatabaseRouter
from .models import AgentResult
from .orchestration import plan_with_llm
from .reporting import build_public_report
from .skills import build_skill_registry
from .skills.base import SkillContext

_SESSION_HISTORY: dict[str, list[dict[str, Any]]] = defaultdict(list)
_SESSION_LOCK = Lock()
_MAX_SESSION_ITEMS = 8


def _compact_evidence(skill: str, evidence: dict[str, Any]) -> dict[str, Any]:
    keep_by_skill = {
        "state_complexity": ["borohydride_summary", "state_counts", "family_counts", "caveats"],
        "state_sequence_lookup": ["target_system", "sequence_label", "sequence_supported", "caveats"],
        "conductivity_loading": ["systems", "temperature_windows", "n_records", "n_doi", "caveats"],
        "h2_release_loading": ["systems", "n_records", "n_doi", "caveats"],
        "dual_axis_cross_database": ["n_conductivity_records", "n_h2_release_records", "caveats"],
        "mechanism_synthesis": ["candidate_comparison", "working_hypothesis", "caveats"],
    }
    return {key: evidence.get(key) for key in keep_by_skill.get(skill, []) if key in evidence}


def _get_session_history(session_id: str | None) -> list[dict[str, Any]]:
    if not session_id:
        return []
    with _SESSION_LOCK:
        return list(_SESSION_HISTORY.get(session_id, []))


def _store_session_evidence(session_id: str | None, skill: str, evidence: dict[str, Any]) -> None:
    if not session_id:
        return
    item = {"skill": skill, "evidence": _compact_evidence(skill, evidence)}
    with _SESSION_LOCK:
        history = _SESSION_HISTORY[session_id]
        history.append(item)
        del history[:-_MAX_SESSION_ITEMS]


def clear_session(session_id: str) -> None:
    with _SESSION_LOCK:
        _SESSION_HISTORY.pop(session_id, None)


def run_agent(
    message: str,
    session_id: str | None = None,
    raw_dir: Path = RAW_DIR,
    out_dir: Path = OUTPUT_DIR,
) -> AgentResult:
    raw_dir = Path(raw_dir)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    plan_obj = plan_with_llm(message)
    registry = build_skill_registry()
    skill = registry.get(plan_obj.skill)

    parameters = dict(plan_obj.parameters or {})
    if parameters.get("use_previous_evidence"):
        parameters["previous_evidence"] = _get_session_history(session_id)

    context = SkillContext(
        raw_dir=raw_dir,
        output_dir=out_dir,
        user_request=message,
        parameters=parameters,
    )
    skill_result = skill.run(context)
    evidence = dict(skill_result.evidence or {})

    show_figure = bool(parameters.get("show_figure", getattr(skill, "produces_figure", False)))
    show_data_files = bool(parameters.get("show_data_files", True))
    figure_suffixes = {".png", ".jpg", ".jpeg", ".svg", ".pdf", ".webp"}
    data_suffixes = {".csv", ".tsv", ".xlsx", ".xls", ".json"}

    files: list[str] = []
    for item in skill_result.files or []:
        path = Path(item)
        suffix = path.suffix.lower()
        if suffix in figure_suffixes and not show_figure:
            continue
        if suffix in data_suffixes and not show_data_files:
            continue
        files.append(str(path))

    router = DatabaseRouter(raw_dir=raw_dir, output_dir=out_dir)
    coverage: dict[str, Any] = {}
    for database in plan_obj.databases:
        try:
            frame = router.load(database)
            coverage[database] = {
                "records_available": int(len(frame)),
                "source_file": router.path_for(database).name,
            }
        except Exception as exc:
            coverage[database] = {"error": f"{type(exc).__name__}: {exc}"}
    evidence["database_coverage"] = coverage
    evidence["output_policy"] = {
        "show_figure": show_figure,
        "show_table": bool(parameters.get("show_table", True)),
        "show_data_files": show_data_files,
        "show_plot_code": bool(parameters.get("show_plot_code", False)),
    }

    plan = {
        "databases": list(plan_obj.databases),
        "skill": plan_obj.skill,
        "parameters": {key: value for key, value in parameters.items() if key != "previous_evidence"},
        "routing": plan_obj.explanation,
        "session_id": session_id,
    }
    answer = build_public_report(message, plan, evidence, files)
    _store_session_evidence(session_id, str(plan_obj.skill), evidence)

    return AgentResult(
        answer=answer,
        files=files,
        data_preview=[],
        plan=plan,
        evidence=evidence,
    )
