from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from .llm import synthesize

MAX_ROWS = 12


def _text(value: Any, default: str = "—") -> str:
    if value is None:
        return default
    try:
        if pd.isna(value):
            return default
    except Exception:
        pass
    text = str(value).strip()
    return text if text and text.lower() != "nan" else default


def _number(value: Any) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return _text(value)
    if number == 0:
        return "0"
    if abs(number) < 1e-3 or abs(number) >= 1e4:
        return f"{number:.3e}"
    return f"{number:.4g}"


def _table(rows: list[dict[str, Any]], columns: list[tuple[str, str]], max_rows: int = MAX_ROWS) -> str:
    if not rows:
        return "_No screened records were returned._"
    visible = rows[:max_rows]
    header = "| " + " | ".join(label for _, label in columns) + " |"
    separator = "| " + " | ".join("---" for _ in columns) + " |"
    body = []
    for row in visible:
        values = []
        for key, _ in columns:
            value = row.get(key, "—")
            if isinstance(value, float):
                value = _number(value)
            values.append(_text(value).replace("|", "\\|").replace("\n", " "))
        body.append("| " + " | ".join(values) + " |")
    output = "\n".join([header, separator, *body])
    if len(rows) > max_rows:
        output += f"\n\n_Showing {max_rows} of {len(rows)} rows; see the exported CSV for all records._"
    return output


def _actions(evidence: dict[str, Any]) -> str:
    items = evidence.get("actions", [])
    return "\n".join(f"{index}. {_text(item)}" for index, item in enumerate(items, 1)) or "_No actions were recorded._"


def _caveats(evidence: dict[str, Any]) -> str:
    items = evidence.get("caveats", [])
    if not items:
        return "_No additional caveats were recorded._"
    return "\n".join(f"- {_text(item)}" for item in items)


def _state_complexity(evidence: dict[str, Any]) -> str:
    summary = evidence.get("borohydride_summary", {})
    summary_text = (
        f"Borohydride records: solid = **{summary.get('solid', 0)}**, "
        f"mixed/transition = **{summary.get('mixed/transition', 0)}**, "
        f"liquid = **{summary.get('liquid', 0)}**."
    )
    return "\n\n".join(
        [
            "### Family-level result",
            summary_text,
            _table(
                evidence.get("family_state_counts", []),
                [
                    ("material_family", "Material family"),
                    ("solid", "Solid"),
                    ("mixed/transition", "Mixed/transition"),
                    ("liquid", "Liquid"),
                    ("total", "Total records"),
                ],
            ),
        ]
    )


def _state_sequence(evidence: dict[str, Any]) -> str:
    result = (
        f"Sequence for **{evidence.get('target_system', 'target system')}**: "
        f"**{evidence.get('sequence_label', 'not available')}**. "
        f"Re-entrant sequence supported: **{evidence.get('sequence_supported', False)}**."
    )
    return "\n\n".join(
        [
            "### Composition-dependent sequence",
            result,
            _table(
                evidence.get("public_rows", []),
                [
                    ("formula", "Composition"),
                    ("NH3_per_BH4", "NH₃/BH₄"),
                    ("reported_state", "Reported state"),
                    ("phase_change", "Phase description"),
                    ("conditions", "Conditions"),
                    ("evidence_type", "Evidence type"),
                    ("confidence", "Confidence"),
                    ("doi", "DOI"),
                ],
            ),
        ]
    )


def _conductivity(evidence: dict[str, Any]) -> str:
    return "\n\n".join(
        [
            "### DOI-aware conductivity evidence",
            f"Aggregated points: **{evidence.get('n_records', 0)}**; unique DOI: **{evidence.get('n_doi', 0)}**.",
            _table(
                evidence.get("public_rows", []),
                [
                    ("formula", "Composition"),
                    ("NH3_per_BH4", "NH₃/BH₄"),
                    ("conductivity_geomean_S_cm", "Conductivity (S cm⁻¹)"),
                    ("selected_T_mean_K", "Mean T (K)"),
                    ("n_DOI", "n DOI"),
                    ("DOI_list", "DOI"),
                ],
            ),
        ]
    )


def _h2_release(evidence: dict[str, Any]) -> str:
    return "\n\n".join(
        [
            "### Condition-aware H₂-release evidence",
            f"Records: **{evidence.get('n_records', 0)}**; unique DOI: **{evidence.get('n_doi', 0)}**.",
            _table(
                evidence.get("public_rows", []),
                [
                    ("formula", "Composition"),
                    ("NH3_per_BH4", "NH₃/BH₄"),
                    ("H2_release_wt_percent", "H₂ release (wt%)"),
                    ("temperature", "Temperature"),
                    ("conditions", "Conditions"),
                    ("DOI", "DOI"),
                ],
            ),
        ]
    )


def _mechanism(evidence: dict[str, Any]) -> str:
    fact_table = _table(
        evidence.get("evidence_facts", []),
        [("level", "Evidence level"), ("statement", "Statement"), ("source_skill", "Source skill")],
    )
    comparison = _table(
        evidence.get("candidate_comparison", []),
        [("candidate", "Candidate explanation"), ("support", "Support"), ("assessment", "Assessment")],
    )
    hypothesis = evidence.get("working_hypothesis", {})
    return "\n\n".join(
        [
            "### Evidence hierarchy",
            fact_table,
            "### Competing explanations",
            comparison,
            "### Working hypothesis",
            _text(hypothesis.get("statement")),
            "**Validation targets:** " + "; ".join(hypothesis.get("required_validation", [])),
        ]
    )


def _computational(evidence: dict[str, Any]) -> str:
    systems = _table(evidence.get("target_systems", []), [("formula", "System"), ("role", "Role")])
    workflow_lines = []
    for stage in evidence.get("workflow", []):
        tasks = " ".join(f"{index}. {task}" for index, task in enumerate(stage.get("tasks", []), 1))
        workflow_lines.append(f"**{stage.get('stage', 'Stage')}:** {tasks}")
    expected = _table(evidence.get("expected_observations", []), [("system", "System"), ("expected", "Expected observation")])
    falsification = "\n".join(f"- {item}" for item in evidence.get("falsification_criteria", []))
    return "\n\n".join(
        [
            "### Target systems",
            systems,
            "### Workflow",
            "\n\n".join(workflow_lines),
            "### Expected observations",
            expected,
            "### Falsification criteria",
            falsification,
        ]
    )


def build_public_report(
    request: str,
    plan: dict[str, Any],
    evidence: dict[str, Any],
    files: list[str],
) -> str:
    skill = str(plan.get("skill") or "none")
    databases = plan.get("databases", [])
    sections = [
        "## Investigation",
        f"**Question:** {request}",
        "**Selected databases:** " + (", ".join(databases) if databases else "none"),
        f"**Selected skill:** `{skill}`",
        f"**Routing:** {_text(plan.get('routing'))}",
        "## Data-access and analysis actions",
        _actions(evidence),
        "## Evidence",
    ]

    if skill == "state_complexity":
        sections.append(_state_complexity(evidence))
    elif skill == "state_sequence_lookup":
        sections.append(_state_sequence(evidence))
    elif skill == "conductivity_loading":
        sections.append(_conductivity(evidence))
    elif skill == "h2_release_loading":
        sections.append(_h2_release(evidence))
    elif skill == "dual_axis_cross_database":
        sections.append(_conductivity(evidence.get("digbat", {})))
        sections.append(_h2_release(evidence.get("dighyd", {})))
    elif skill == "mechanism_synthesis":
        sections.append(_mechanism(evidence))
    elif skill == "computational_design":
        sections.append(_computational(evidence))
    else:
        sections.append("```json\n" + json.dumps(evidence, indent=2, ensure_ascii=False, default=str)[:16000] + "\n```")

    sections.extend(["## Caveats", _caveats(evidence)])

    if files:
        sections.extend(
            [
                "## Generated artifacts",
                "\n".join(f"- `{Path(path).name}`" for path in files),
            ]
        )

    compact_evidence = {
        key: evidence.get(key)
        for key in [
            "sequence_label",
            "sequence_supported",
            "borohydride_summary",
            "n_records",
            "n_doi",
            "candidate_comparison",
            "working_hypothesis",
            "caveats",
        ]
        if key in evidence
    }
    interpretation = synthesize(request, compact_evidence)
    sections.extend(
        [
            "## Conclusion",
            interpretation
            or "The conclusion is limited to the screened records and deterministic skill output above; no unsupported values or mechanisms were added.",
        ]
    )
    return "\n\n".join(sections)
