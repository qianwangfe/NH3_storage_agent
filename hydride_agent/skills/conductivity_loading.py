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
from .common import choose_column, host_system_base, nh3_per_bh4, pure_parent_or_ammine

DEFAULT_TEMPERATURE_WINDOWS = {
    "LiBH4": [310.0, 3.0],
    "Mg(BH4)2": [310.0, 3.0],
}


def _window_for_system(system: str, parameters: dict) -> tuple[float, float]:
    windows = parameters.get("temperature_windows", DEFAULT_TEMPERATURE_WINDOWS)
    center, half_width = windows.get(system, [305.0, 3.0])
    return float(center), float(half_width)


def _plot_conductivity_loading(data: pd.DataFrame, figure_path: Path) -> None:
    fig, ax = plt.subplots(figsize=(10.5, 6.6))

    for system, group in data.groupby("system_base"):
        group = group.sort_values("NH3_per_BH4")
        conductivity = group["conductivity_geomean_S_cm"].to_numpy(dtype=float)
        error = np.vstack(
            [
                group["yerr_lower_S_cm"].to_numpy(dtype=float),
                group["yerr_upper_S_cm"].to_numpy(dtype=float),
            ]
        )
        target_temperature = float(group["target_T_K"].iloc[0])
        half_width = float(group["temperature_half_width_K"].iloc[0])
        label = f"{system}, {target_temperature:g} ± {half_width:g} K"

        line = ax.errorbar(
            group["NH3_per_BH4"],
            conductivity,
            yerr=error,
            fmt="o",
            markersize=9,
            capsize=5,
            markerfacecolor="white",
            markeredgewidth=1.8,
            label=label,
        )
        if len(group) >= 2:
            ax.plot(
                group["NH3_per_BH4"],
                conductivity,
                "--",
                linewidth=2.0,
                color=line[0].get_color(),
            )

    ax.set_yscale("log")
    ax.set_xlabel("NH₃/BH₄ molar ratio", fontsize=15)
    ax.set_ylabel("Ionic conductivity (S cm⁻¹)", fontsize=15)
    ax.set_title("DigBat conductivity under system-specific temperature windows", fontsize=15, pad=12)
    ax.tick_params(labelsize=12)
    ax.legend(fontsize=10, loc="best")
    ax.grid(True, axis="y", alpha=0.25)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    fig.savefig(figure_path, dpi=240, bbox_inches="tight")
    plt.close(fig)


class ConductivityLoadingSkill:
    name = "conductivity_loading"
    description = (
        "Plot DigBat ionic conductivity against NH3/BH4 using one representative "
        "value per formula and DOI and log10-space cross-study statistics."
    )
    databases = ("digbat",)
    produces_figure = True
    produces_table = True

    def matches(self, request: str) -> float:
        query = request.lower()
        return 5.0 if any(token in query for token in ["conductivity", "digbat", "ionic conductivity"]) else 0.0

    def run(self, context: SkillContext) -> SkillResult:
        router = DatabaseRouter(raw_dir=context.raw_dir, output_dir=context.output_dir)
        source_df = router.load("digbat")

        formula_col = choose_column(source_df, ["Pretty_Formula", "formula"])
        doi_col = choose_column(source_df, ["DOI", "doi"])
        conductivity_col = choose_column(source_df, ["Ion_Conductivity", "ionic conductivity"])
        temperature_col = choose_column(source_df, ["T_Kelvin", "temperature K"])
        if not all([formula_col, doi_col, conductivity_col, temperature_col]):
            raise KeyError("DigBat is missing one or more required columns.")

        work = source_df.copy()
        work = work[work[formula_col].map(pure_parent_or_ammine)].copy()
        work[conductivity_col] = pd.to_numeric(work[conductivity_col], errors="coerce")
        work[temperature_col] = pd.to_numeric(work[temperature_col], errors="coerce")
        work = work.dropna(subset=[formula_col, doi_col, conductivity_col, temperature_col])
        work = work[work[conductivity_col] > 0].copy()
        work["system_base"] = work[formula_col].map(host_system_base)
        work["NH3_per_BH4"] = work[formula_col].map(nh3_per_bh4)

        keep_systems = [str(system) for system in context.parameters.get("systems", ["LiBH4", "Mg(BH4)2"])]
        work = work[work["system_base"].isin(keep_systems)].copy()

        representative_rows: list[dict[str, object]] = []
        for (formula, doi), group in work.groupby([formula_col, doi_col], dropna=False):
            system = str(group["system_base"].iloc[0])
            center, half_width = _window_for_system(system, context.parameters)
            window = group[group[temperature_col].between(center - half_width, center + half_width)].copy()
            if window.empty:
                continue
            window["distance_to_target_K"] = (window[temperature_col] - center).abs()
            nearest = window[window["distance_to_target_K"] == window["distance_to_target_K"].min()]
            representative_rows.append(
                {
                    "formula": str(formula),
                    "system_base": system,
                    "NH3_per_BH4": float(nearest["NH3_per_BH4"].iloc[0]),
                    "DOI": str(doi),
                    "target_T_K": center,
                    "temperature_half_width_K": half_width,
                    "selected_T_K": float(nearest[temperature_col].mean()),
                    "selected_conductivity_S_cm": float(nearest[conductivity_col].mean()),
                    "value_type": "nearest direct record within the configured window",
                }
            )

        representative_df = pd.DataFrame(representative_rows)
        if representative_df.empty:
            raise ValueError(
                "No DigBat records remained after formula, system, temperature-window, and DOI screening."
            )

        aggregate_rows: list[dict[str, object]] = []
        for (formula, system, ratio), group in representative_df.groupby(
            ["formula", "system_base", "NH3_per_BH4"], dropna=False
        ):
            values = group["selected_conductivity_S_cm"].to_numpy(dtype=float)
            log_values = np.log10(values)
            mean_log = float(log_values.mean())
            sd_log = float(log_values.std(ddof=1)) if len(log_values) > 1 else 0.0
            center = 10 ** mean_log
            lower = 10 ** (mean_log - sd_log)
            upper = 10 ** (mean_log + sd_log)
            aggregate_rows.append(
                {
                    "formula": formula,
                    "system_base": system,
                    "NH3_per_BH4": float(ratio),
                    "n_DOI": int(group["DOI"].astype(str).nunique()),
                    "conductivity_geomean_S_cm": center,
                    "conductivity_lower_1SD_S_cm": lower,
                    "conductivity_upper_1SD_S_cm": upper,
                    "yerr_lower_S_cm": center - lower,
                    "yerr_upper_S_cm": upper - center,
                    "selected_T_mean_K": float(group["selected_T_K"].mean()),
                    "target_T_K": float(group["target_T_K"].iloc[0]),
                    "temperature_half_width_K": float(group["temperature_half_width_K"].iloc[0]),
                    "DOI_list": "; ".join(sorted(group["DOI"].astype(str).unique())),
                    "value_type": "cross-DOI geometric mean in log10 conductivity space",
                }
            )

        aggregate_df = pd.DataFrame(aggregate_rows).sort_values(
            ["system_base", "NH3_per_BH4", "formula"]
        ).reset_index(drop=True)

        context.output_dir.mkdir(parents=True, exist_ok=True)
        representative_path = context.output_dir / "skill_conductivity_one_point_per_DOI.csv"
        data_path = context.output_dir / "skill_conductivity_loading.csv"
        figure_path = context.output_dir / "skill_conductivity_loading.png"
        representative_df.to_csv(representative_path, index=False, encoding="utf-8-sig")
        aggregate_df.to_csv(data_path, index=False, encoding="utf-8-sig")
        _plot_conductivity_loading(aggregate_df, figure_path)

        evidence = {
            "database": "digbat",
            "source_file": router.path_for("digbat").name,
            "systems": keep_systems,
            "temperature_windows": {
                system: list(_window_for_system(system, context.parameters)) for system in keep_systems
            },
            "n_records": int(len(aggregate_df)),
            "n_representative_doi_rows": int(len(representative_df)),
            "n_doi": int(representative_df["DOI"].astype(str).nunique()),
            "public_rows": aggregate_df.to_dict(orient="records"),
            "actions": [
                "Loaded DigBat conductivity records.",
                "Kept pure parent borohydrides and pure borohydride ammines.",
                "Calculated the parent host and NH3/BH4 ratio from each formula.",
                "Applied system-specific temperature windows.",
                "Selected one representative conductivity value per formula and DOI.",
                "Calculated cross-DOI geometric means and one-standard-deviation bounds in log10 space.",
                "Exported DOI-level and aggregated plotting tables.",
            ],
            "caveats": [
                "LiBH4 and Mg(BH4)2 are compared under different temperature windows.",
                "Connecting lines are visual guides within each host system and are not kinetic models.",
            ],
            "plot_code": inspect.getsource(_plot_conductivity_loading),
        }

        return SkillResult(
            skill=self.name,
            files=[figure_path, data_path, representative_path],
            evidence=evidence,
            message="Generated DOI-aware conductivity-versus-loading evidence.",
        )
