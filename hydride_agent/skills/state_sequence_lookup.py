from __future__ import annotations

from pathlib import Path

import pandas as pd

from ..database_tools import DatabaseRouter
from .base import SkillContext, SkillResult
from .common import (
    choose_column,
    host_system_base,
    join_nonempty,
    nh3_per_bh4,
    normalize_state,
    safe_text,
)


def _is_single_host_formula(formula: str, target_system: str) -> bool:
    text = str(formula)
    if host_system_base(text) != target_system:
        return False

    # Avoid mixed-cation or composite records when tracing a single host sequence.
    host_tokens = ["LiBH4", "NaBH4", "KBH4", "Mg(BH4)2", "Ca(BH4)2"]
    present = [token for token in host_tokens if token in text]
    return len(set(present)) <= 1


def _sequence_summary(rows: pd.DataFrame) -> tuple[str, bool, list[str]]:
    if rows.empty:
        return "not available", False, ["No matching records were found."]

    target_states: list[str] = []
    caveats: list[str] = []
    for target_ratio in [1.0, 2.0, 3.0]:
        candidates = rows[(rows["NH3_per_BH4"] - target_ratio).abs() <= 0.15]
        if candidates.empty:
            target_states.append("missing")
            caveats.append(f"No record was found near NH3/BH4 = {target_ratio:g}.")
            continue
        state = str(candidates.iloc[0]["reported_state"])
        target_states.append(state)

    label_map = {
        "solid": "solid",
        "mixed/transition": "mixed/transition (liquid-like)",
        "liquid": "liquid",
        "not reported": "not reported",
        "missing": "missing",
    }
    sequence_label = " → ".join(label_map.get(state, state) for state in target_states)
    supported = (
        target_states[0] == "solid"
        and target_states[1] in {"mixed/transition", "liquid"}
        and target_states[2] == "solid"
    )

    if supported:
        caveats.append(
            "The database supports a solid–liquid-like–solid sequence, but the x ≈ 2 label is condition-dependent and may be reported as pseudo-liquid or mixed/transition."
        )
    return sequence_label, supported, caveats


class StateSequenceLookupSkill:
    name = "state_sequence_lookup"
    description = (
        "Trace a composition-dependent state sequence for one borohydride host, "
        "including loading, conditions, evidence type, confidence, and DOI."
    )
    databases = ("nh3_storage",)
    produces_figure = False
    produces_table = True

    def matches(self, request: str) -> float:
        query = request.lower()
        keywords = [
            "state sequence",
            "solid-liquid-solid",
            "solid–liquid–solid",
            "solid → liquid → solid",
            "non-monotonic state",
            "libh4",
        ]
        return 6.0 if any(keyword in query for keyword in keywords) else 0.0

    def run(self, context: SkillContext) -> SkillResult:
        router = DatabaseRouter(raw_dir=context.raw_dir, output_dir=context.output_dir)
        source_df = router.load("nh3_storage")

        target_system = str(context.parameters.get("target_system", "LiBH4"))
        min_ratio = float(context.parameters.get("min_ratio", 0.5))
        max_ratio = float(context.parameters.get("max_ratio", 3.5))

        before_col = choose_column(source_df, ["Material components (before NH3 absorption)"])
        after_col = choose_column(source_df, ["Material components (after NH3 absorption)"])
        state_col = choose_column(source_df, ["materials state"])
        phase_col = choose_column(source_df, ["Phase change"])
        doi_col = choose_column(source_df, ["doi", "DOI"])
        temperature_col = choose_column(source_df, ["temperature in PCI", "temperature"])
        pressure_col = choose_column(source_df, ["Ammonia pressure", "Plateau pressure", "pressure"])
        method_col = choose_column(source_df, ["Methods", "Observation methods"])
        record_type_col = choose_column(source_df, ["record_type", "article type"])
        confidence_col = choose_column(source_df, ["overall_confidence", "confidence"])
        notes_col = choose_column(source_df, ["review_notes", "notes", "remarks"])

        rows: list[dict[str, object]] = []
        for _, source_row in source_df.iterrows():
            before = safe_text(source_row.get(before_col) if before_col else None)
            after = safe_text(source_row.get(after_col) if after_col else None)
            formula = after if after != "—" else before

            if not _is_single_host_formula(formula, target_system):
                continue

            ratio = nh3_per_bh4(formula)
            if pd.isna(ratio) or not (min_ratio <= float(ratio) <= max_ratio):
                continue

            state_raw = safe_text(source_row.get(state_col) if state_col else None, "")
            phase_raw = safe_text(source_row.get(phase_col) if phase_col else None, "")
            state = normalize_state(state_raw)
            evidence_type = "explicit state label" if state != "not reported" else "inferred from phase description"
            if state == "not reported":
                state = normalize_state(phase_raw)

            rows.append(
                {
                    "formula": formula,
                    "host_system": target_system,
                    "NH3_per_BH4": float(ratio),
                    "reported_state": state,
                    "state_label_raw": state_raw or phase_raw or "—",
                    "phase_change": phase_raw or "—",
                    "conditions": join_nonempty(
                        [
                            source_row.get(temperature_col) if temperature_col else None,
                            source_row.get(pressure_col) if pressure_col else None,
                            source_row.get(method_col) if method_col else None,
                        ]
                    ),
                    "evidence_type": evidence_type,
                    "record_type": safe_text(source_row.get(record_type_col) if record_type_col else None),
                    "confidence": safe_text(source_row.get(confidence_col) if confidence_col else None),
                    "doi": safe_text(source_row.get(doi_col) if doi_col else None),
                    "notes": safe_text(source_row.get(notes_col) if notes_col else None),
                }
            )

        work = pd.DataFrame(rows)
        if work.empty:
            raise ValueError(
                f"No {target_system} state records remained within NH3/BH4 = {min_ratio:g}–{max_ratio:g}."
            )

        work = work.sort_values(["NH3_per_BH4", "formula", "doi"]).drop_duplicates(
            subset=["formula", "reported_state", "doi"], keep="first"
        )
        work = work.reset_index(drop=True)

        sequence_label, sequence_supported, caveats = _sequence_summary(work)

        context.output_dir.mkdir(parents=True, exist_ok=True)
        data_path = context.output_dir / "skill_state_sequence_lookup.csv"
        work.to_csv(data_path, index=False, encoding="utf-8-sig")

        evidence = {
            "database": "nh3_storage",
            "source_file": router.path_for("nh3_storage").name,
            "target_system": target_system,
            "ratio_range": [min_ratio, max_ratio],
            "n_records": int(len(work)),
            "public_rows": work.to_dict(orient="records"),
            "sequence_label": sequence_label,
            "sequence_supported": sequence_supported,
            "caveats": caveats
            + [
                "State labels should not be compared without retaining temperature, pressure, atmosphere, and sample-history information.",
                "The sequence is a literature-evidence summary, not an equilibrium phase diagram.",
            ],
            "actions": [
                "Loaded the curated NH3 Storage workbook.",
                f"Restricted records to the single-host {target_system} system.",
                f"Restricted NH3/BH4 to {min_ratio:g}–{max_ratio:g}.",
                "Extracted reported state, phase description, conditions, evidence type, confidence, and DOI.",
                "Sorted records by NH3/BH4 ratio and evaluated the x ≈ 1, 2, and 3 sequence.",
            ],
        }

        return SkillResult(
            skill=self.name,
            files=[data_path],
            evidence=evidence,
            message=f"Traced the reported state sequence for {target_system}.",
        )
