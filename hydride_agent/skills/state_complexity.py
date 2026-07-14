from __future__ import annotations

import inspect
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from ..database_tools import DatabaseRouter
from .base import SkillContext, SkillResult
from .common import choose_column, family_from_text, join_nonempty, normalize_state, safe_text

STATE_ORDER = ["solid", "mixed/transition", "liquid"]


def _plot_state_complexity(counts: pd.DataFrame, figure_path: Path) -> None:
    fig, ax = plt.subplots(figsize=(10.5, 5.8))
    y = np.arange(len(counts))
    left = np.zeros(len(counts), dtype=float)

    containers = []
    for state in STATE_ORDER:
        values = counts[state].to_numpy(dtype=float)
        container = ax.barh(y, values, left=left, height=0.62, label=state)
        containers.append(container)
        for index, (value, left_edge) in enumerate(zip(values, left)):
            if value > 0:
                ax.text(
                    left_edge + value / 2,
                    index,
                    str(int(value)),
                    ha="center",
                    va="center",
                    fontsize=11,
                )
        left += values

    labels = counts["material_family"].astype(str).tolist()
    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=12)

    for tick, label in zip(ax.get_yticklabels(), labels):
        if label == "borohydride":
            tick.set_fontweight("bold")
            tick.set_text("borohydride  ★")

    borohydride_indices = counts.index[counts["material_family"] == "borohydride"].tolist()
    for index in borohydride_indices:
        for container in containers:
            patch = container.patches[index]
            patch.set_linewidth(2.0)
            patch.set_edgecolor("black")
            patch.set_hatch("//")

    ax.set_xlabel("Number of NH₃-storage literature records", fontsize=14)
    ax.set_title("Reported physical-state diversity by material family", fontsize=16, pad=12)
    ax.tick_params(axis="x", labelsize=12)
    ax.legend(title="Reported state", fontsize=11, title_fontsize=11)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    maximum = float(counts["total"].max()) if len(counts) else 1.0
    ax.set_xlim(0, max(1.0, maximum * 1.15))
    fig.tight_layout()
    fig.savefig(figure_path, dpi=240, bbox_inches="tight")
    plt.close(fig)


class StateComplexitySkill:
    name = "state_complexity"
    description = (
        "Compare raw solid, mixed/transition, and liquid record counts across "
        "NH3-storage material families and highlight borohydrides."
    )
    databases = ("nh3_storage",)
    produces_figure = True
    produces_table = True

    def matches(self, request: str) -> float:
        query = request.lower()
        keywords = [
            "state diversity",
            "material families",
            "family-by-state",
            "state distribution",
            "raw counts",
        ]
        return 6.0 if any(keyword in query for keyword in keywords) else 0.0

    def run(self, context: SkillContext) -> SkillResult:
        router = DatabaseRouter(raw_dir=context.raw_dir, output_dir=context.output_dir)
        source_df = router.load("nh3_storage")

        before_col = choose_column(source_df, ["Material components (before NH3 absorption)"])
        after_col = choose_column(source_df, ["Material components (after NH3 absorption)"])
        type_col = choose_column(source_df, ["Types of materials"])
        state_col = choose_column(source_df, ["materials state"])
        phase_col = choose_column(source_df, ["Phase change"])
        doi_col = choose_column(source_df, ["doi", "DOI"])
        temperature_col = choose_column(source_df, ["temperature in PCI", "temperature"])
        pressure_col = choose_column(source_df, ["Ammonia pressure", "Plateau pressure", "pressure"])
        method_col = choose_column(source_df, ["Methods", "Observation methods"])

        rows: list[dict[str, object]] = []
        for _, source_row in source_df.iterrows():
            before = safe_text(source_row.get(before_col) if before_col else None)
            after = safe_text(source_row.get(after_col) if after_col else None)
            type_text = safe_text(source_row.get(type_col) if type_col else None, "")
            state_raw = safe_text(source_row.get(state_col) if state_col else None, "")
            phase_raw = safe_text(source_row.get(phase_col) if phase_col else None, "")

            state = normalize_state(state_raw)
            if state == "not reported":
                state = normalize_state(phase_raw)
            if state not in STATE_ORDER:
                continue

            family = family_from_text(" | ".join([type_text, before, after]))
            if family == "other" and not bool(context.parameters.get("include_other", False)):
                continue

            rows.append(
                {
                    "formula": after if after != "—" else before,
                    "material_family": family,
                    "reported_state": state,
                    "state_label_raw": state_raw or phase_raw or "—",
                    "conditions": join_nonempty(
                        [
                            source_row.get(temperature_col) if temperature_col else None,
                            source_row.get(pressure_col) if pressure_col else None,
                            source_row.get(method_col) if method_col else None,
                        ]
                    ),
                    "doi": safe_text(source_row.get(doi_col) if doi_col else None),
                }
            )

        work = pd.DataFrame(rows)
        if work.empty:
            raise ValueError("No state-labelled NH3-storage records were found.")

        counts = (
            work.groupby(["material_family", "reported_state"])
            .size()
            .unstack(fill_value=0)
            .reindex(columns=STATE_ORDER, fill_value=0)
            .reset_index()
        )
        counts["total"] = counts[STATE_ORDER].sum(axis=1)
        counts = counts.sort_values("total", ascending=True).reset_index(drop=True)

        context.output_dir.mkdir(parents=True, exist_ok=True)
        figure_path = context.output_dir / "skill_state_complexity.png"
        count_path = context.output_dir / "skill_state_complexity_counts.csv"
        record_path = context.output_dir / "skill_state_complexity_records.csv"

        _plot_state_complexity(counts, figure_path)
        counts.to_csv(count_path, index=False, encoding="utf-8-sig")
        work.to_csv(record_path, index=False, encoding="utf-8-sig")

        borohydride = counts[counts["material_family"] == "borohydride"]
        borohydride_summary = (
            borohydride.iloc[0].to_dict() if not borohydride.empty else {}
        )

        evidence = {
            "database": "nh3_storage",
            "source_file": router.path_for("nh3_storage").name,
            "n_records": int(len(work)),
            "n_materials": int(work["formula"].astype(str).nunique()),
            "state_counts": {
                state: int((work["reported_state"] == state).sum())
                for state in STATE_ORDER
            },
            "family_counts": {
                str(key): int(value)
                for key, value in work["material_family"].value_counts().items()
            },
            "borohydride_summary": borohydride_summary,
            "public_rows": work.to_dict(orient="records"),
            "family_state_counts": counts.to_dict(orient="records"),
            "actions": [
                "Loaded the curated NH3 Storage workbook.",
                "Normalized reported state labels into solid, mixed/transition, and liquid.",
                "Grouped literature records by material family rather than unique formula count.",
                "Highlighted borohydrides as the family with the broadest state diversity.",
                "Exported the record-level table and family-level count table.",
            ],
            "plot_code": inspect.getsource(_plot_state_complexity),
            "caveats": [
                "Counts represent literature records, not independent materials.",
                "Reported state depends on temperature, pressure, atmosphere, and sample history.",
            ],
        }

        return SkillResult(
            skill=self.name,
            files=[figure_path, count_path, record_path],
            evidence=evidence,
            message="Generated family-level NH3-storage state statistics.",
        )
