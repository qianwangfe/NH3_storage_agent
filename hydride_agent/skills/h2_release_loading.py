from __future__ import annotations

import inspect
import re
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from ..database_tools import DatabaseRouter
from .base import SkillContext, SkillResult
from .common import choose_column, host_system_base, nh3_per_bh4, pure_parent_or_ammine, safe_text


def _extract_formula(text: object) -> str | None:
    source = str(text or "").replace("∙", "·")
    patterns = [
        r"([A-Z][a-z]?(?:\d+(?:\.\d+)?)?\(BH4\)\d+(?:(?:[·-]\d*(?:\.\d+)?NH3)|(?:\(NH3\)\d+))*)",
        r"([A-Z][a-z]?(?:\d+(?:\.\d+)?)?BH4(?:(?:[·-]\d*(?:\.\d+)?NH3)|(?:\(NH3\)\d+))*)",
    ]
    for pattern in patterns:
        match = re.search(pattern, source)
        if match:
            return match.group(1)
    return None


def _extract_wt_percent(text: object) -> float | None:
    match = re.search(
        r"(\d+(?:\.\d+)?)\s*(?:wt\.?\s*%|mass\s*%|wt%)",
        str(text or ""),
        flags=re.I,
    )
    return float(match.group(1)) if match else None


def _plot_h2_release_loading(data: pd.DataFrame, figure_path: Path) -> None:
    fig, ax = plt.subplots(figsize=(10.5, 6.6))

    for system, group in data.groupby("system_base"):
        ax.scatter(
            group["NH3_per_BH4"],
            group["H2_release_wt_percent"],
            s=100,
            marker="s",
            label=f"{system} (n={len(group)})",
        )

    ax.set_xlabel("NH₃/BH₄ molar ratio", fontsize=15)
    ax.set_ylabel("Reported H₂ release (wt%)", fontsize=15)
    ax.set_title("DigHyd records for ammoniated borohydrides", fontsize=16, pad=12)
    ax.tick_params(labelsize=12)
    ax.legend(fontsize=10, loc="best")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.text(
        0.01,
        0.02,
        "Points are not connected across studies or non-comparable conditions.",
        transform=ax.transAxes,
        fontsize=10,
        va="bottom",
    )
    fig.tight_layout()
    fig.savefig(figure_path, dpi=240, bbox_inches="tight")
    plt.close(fig)


class H2ReleaseLoadingSkill:
    name = "h2_release_loading"
    description = (
        "Plot reported H2 release for ammoniated borohydrides while retaining "
        "DOI and condition information and avoiding cross-study trend lines."
    )
    databases = ("dighyd",)
    produces_figure = True
    produces_table = True

    def matches(self, request: str) -> float:
        query = request.lower()
        return 5.0 if any(token in query for token in ["h2 release", "hydrogen release", "dighyd", "hydrogen-storage"]) else 0.0

    def run(self, context: SkillContext) -> SkillResult:
        router = DatabaseRouter(raw_dir=context.raw_dir, output_dir=context.output_dir)
        source_df = router.load("dighyd")

        before_col = choose_column(source_df, ["Material components (before H absorption)"])
        after_col = choose_column(source_df, ["Material components (after H absorption)"])
        doi_col = choose_column(source_df, ["doi", "DOI"])
        temperature_col = choose_column(
            source_df,
            [
                "Dehydrogenation temperature",
                "Hydrogen desorption temperature",
                "Desorption temperature",
                "temperature",
            ],
        )
        condition_col = choose_column(
            source_df,
            ["Hydrogenation and dehygenation conditons", "conditions"],
        )
        wt_columns = [
            column
            for column in source_df.columns
            if "Gravimetric hydrogen densities" in str(column)
        ]

        include_parent = bool(context.parameters.get("include_parent", False))
        min_ratio = float(context.parameters.get("min_ratio", 0.0))
        requested_systems = context.parameters.get("systems")
        requested_systems = [str(item) for item in requested_systems] if requested_systems else None

        rows: list[dict[str, object]] = []
        for _, source_row in source_df.iterrows():
            formula = _extract_formula(source_row.get(before_col, "")) if before_col else None
            if not formula and after_col:
                formula = _extract_formula(source_row.get(after_col, ""))
            if not formula or not pure_parent_or_ammine(formula):
                continue

            wt_percent = None
            for column in wt_columns:
                wt_percent = _extract_wt_percent(source_row.get(column, ""))
                if wt_percent is not None:
                    break
            if wt_percent is None:
                continue

            ratio = nh3_per_bh4(formula)
            if pd.isna(ratio):
                continue
            ratio = float(ratio)
            if not include_parent and ratio <= min_ratio:
                continue

            system = host_system_base(formula)
            if requested_systems and system not in requested_systems:
                continue

            rows.append(
                {
                    "formula": formula,
                    "system_base": system,
                    "NH3_per_BH4": ratio,
                    "H2_release_wt_percent": float(wt_percent),
                    "temperature": safe_text(source_row.get(temperature_col) if temperature_col else None),
                    "conditions": safe_text(source_row.get(condition_col) if condition_col else None),
                    "DOI": safe_text(source_row.get(doi_col) if doi_col else None),
                }
            )

        data = pd.DataFrame(rows)
        if data.empty:
            raise ValueError(
                "No ammoniated borohydride DigHyd records with extractable H2-release values were found."
            )

        data = data.drop_duplicates(
            subset=["formula", "DOI", "H2_release_wt_percent", "temperature"]
        ).sort_values(["system_base", "NH3_per_BH4", "formula", "DOI"])
        data = data.reset_index(drop=True)

        context.output_dir.mkdir(parents=True, exist_ok=True)
        data_path = context.output_dir / "skill_h2_release_loading.csv"
        figure_path = context.output_dir / "skill_h2_release_loading.png"
        data.to_csv(data_path, index=False, encoding="utf-8-sig")
        _plot_h2_release_loading(data, figure_path)

        evidence = {
            "database": "dighyd",
            "source_file": router.path_for("dighyd").name,
            "include_parent_borohydrides": include_parent,
            "n_records": int(len(data)),
            "n_materials": int(data["formula"].astype(str).nunique()),
            "n_doi": int(data["DOI"].astype(str).nunique()),
            "systems": sorted(data["system_base"].astype(str).unique().tolist()),
            "public_rows": data.to_dict(orient="records"),
            "actions": [
                "Loaded DigHyd hydrogen-storage records.",
                "Extracted pure borohydride or borohydride-ammine formulas.",
                "Calculated NH3/BH4 ratios from the formulas.",
                "Excluded parent borohydrides at NH3/BH4 = 0 by default.",
                "Retained reported H2 release, temperature, conditions, and DOI.",
                "Plotted material-level points without connecting non-comparable studies.",
            ],
            "caveats": [
                "Reported H2 release values may use different temperature programs, pressures, and definitions.",
                "The scatter plot is a literature comparison and does not establish a continuous composition trend.",
            ],
            "plot_code": inspect.getsource(_plot_h2_release_loading),
        }

        return SkillResult(
            skill=self.name,
            files=[figure_path, data_path],
            evidence=evidence,
            message="Generated a condition-aware DigHyd H2-release comparison.",
        )
