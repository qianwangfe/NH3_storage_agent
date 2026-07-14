from __future__ import annotations

import inspect
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from .base import SkillContext, SkillResult
from .conductivity_loading import ConductivityLoadingSkill
from .h2_release_loading import H2ReleaseLoadingSkill


def _plot_dual_axis(
    conductivity: pd.DataFrame,
    hydrogen: pd.DataFrame,
    figure_path: Path,
) -> None:
    fig, left = plt.subplots(figsize=(10.8, 6.8))
    right = left.twinx()

    systems = sorted(
        set(conductivity["system_base"].astype(str)).union(
            set(hydrogen["system_base"].astype(str))
        )
    )
    cycle = plt.rcParams["axes.prop_cycle"].by_key()["color"]
    color_map = {system: cycle[index % len(cycle)] for index, system in enumerate(systems)}

    for system, group in conductivity.groupby("system_base"):
        group = group.sort_values("NH3_per_BH4")
        color = color_map[str(system)]
        left.errorbar(
            group["NH3_per_BH4"],
            group["conductivity_geomean_S_cm"],
            yerr=[group["yerr_lower_S_cm"], group["yerr_upper_S_cm"]],
            fmt="o",
            markerfacecolor="white",
            markeredgewidth=1.6,
            capsize=4,
            color=color,
            label=f"{system}: conductivity",
        )
        if len(group) >= 2:
            left.plot(
                group["NH3_per_BH4"],
                group["conductivity_geomean_S_cm"],
                "--",
                color=color,
                linewidth=1.8,
            )

    for system, group in hydrogen.groupby("system_base"):
        color = color_map[str(system)]
        right.scatter(
            group["NH3_per_BH4"],
            group["H2_release_wt_percent"],
            marker="s",
            s=90,
            color=color,
            label=f"{system}: H₂ release",
        )

    left.set_yscale("log")
    left.set_xlabel("NH₃/BH₄ molar ratio", fontsize=15)
    left.set_ylabel("Ionic conductivity (S cm⁻¹)", fontsize=14)
    right.set_ylabel("Reported H₂ release (wt%)", fontsize=14)
    left.set_title("Cross-database comparison with separate property axes", fontsize=15, pad=12)
    left.tick_params(labelsize=11)
    right.tick_params(labelsize=11)
    left.spines["top"].set_visible(False)
    right.spines["top"].set_visible(False)

    handles_left, labels_left = left.get_legend_handles_labels()
    handles_right, labels_right = right.get_legend_handles_labels()
    left.legend(
        handles_left + handles_right,
        labels_left + labels_right,
        fontsize=9,
        loc="best",
    )
    left.text(
        0.01,
        0.02,
        "H₂-release points are not connected across studies or conditions.",
        transform=left.transAxes,
        fontsize=9,
    )
    fig.tight_layout()
    fig.savefig(figure_path, dpi=240, bbox_inches="tight")
    plt.close(fig)


class DualAxisCrossDatabaseSkill:
    name = "dual_axis_cross_database"
    description = (
        "Combine DigBat conductivity and DigHyd H2-release evidence on separate Y axes "
        "while preserving the screening rules of both source skills."
    )
    databases = ("digbat", "dighyd")
    produces_figure = True
    produces_table = True

    def matches(self, request: str) -> float:
        query = request.lower()
        has_conductivity = "conductivity" in query or "digbat" in query
        has_hydrogen = any(token in query for token in ["h2", "hydrogen", "dighyd"])
        return 7.0 if has_conductivity and has_hydrogen else 0.0

    def run(self, context: SkillContext) -> SkillResult:
        conductivity_parameters = dict(context.parameters)
        conductivity_parameters.setdefault("systems", ["LiBH4", "Mg(BH4)2"])
        hydrogen_parameters = dict(context.parameters)
        hydrogen_parameters.setdefault("include_parent", False)

        conductivity_result = ConductivityLoadingSkill().run(
            SkillContext(
                raw_dir=context.raw_dir,
                output_dir=context.output_dir,
                user_request=context.user_request,
                parameters=conductivity_parameters,
            )
        )
        hydrogen_result = H2ReleaseLoadingSkill().run(
            SkillContext(
                raw_dir=context.raw_dir,
                output_dir=context.output_dir,
                user_request=context.user_request,
                parameters=hydrogen_parameters,
            )
        )

        conductivity_path = context.output_dir / "skill_conductivity_loading.csv"
        hydrogen_path = context.output_dir / "skill_h2_release_loading.csv"
        conductivity = pd.read_csv(conductivity_path)
        hydrogen = pd.read_csv(hydrogen_path)

        figure_path = context.output_dir / "skill_dual_axis_cross_database.png"
        _plot_dual_axis(conductivity, hydrogen, figure_path)

        evidence = {
            "databases": ["digbat", "dighyd"],
            "digbat": conductivity_result.evidence,
            "dighyd": hydrogen_result.evidence,
            "n_conductivity_records": int(len(conductivity)),
            "n_h2_release_records": int(len(hydrogen)),
            "actions": [
                "Executed the DOI-aware DigBat conductivity skill.",
                "Executed the condition-aware DigHyd H2-release skill.",
                "Placed conductivity and H2 release on separate Y axes.",
                "Used consistent host-system colors across the two properties.",
                "Did not connect H2-release records across non-comparable studies.",
            ],
            "caveats": [
                "The two Y axes represent different properties and should not be interpreted as a shared scale.",
                "Cross-database co-variation is descriptive and does not establish causality.",
            ],
            "plot_code": inspect.getsource(_plot_dual_axis),
        }

        return SkillResult(
            skill=self.name,
            files=[figure_path, conductivity_path, hydrogen_path],
            evidence=evidence,
            message="Generated a cross-database dual-axis comparison.",
        )
