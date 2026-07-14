from __future__ import annotations

import inspect
from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from .base import SkillContext, SkillResult


def _extract_previous_facts(previous_evidence: list[dict[str, Any]]) -> list[dict[str, str]]:
    facts: list[dict[str, str]] = []
    for item in previous_evidence:
        skill = str(item.get("skill", ""))
        evidence = item.get("evidence", {}) if isinstance(item.get("evidence"), dict) else {}
        if skill == "state_complexity":
            summary = evidence.get("borohydride_summary", {})
            if summary:
                facts.append(
                    {
                        "level": "direct database evidence",
                        "statement": (
                            "Borohydrides contain solid, mixed/transition, and liquid literature records, "
                            "showing broader state diversity than a single-state family description."
                        ),
                        "source_skill": skill,
                    }
                )
        elif skill == "state_sequence_lookup":
            facts.append(
                {
                    "level": "direct database evidence",
                    "statement": (
                        f"The traced {evidence.get('target_system', 'borohydride')} sequence is "
                        f"{evidence.get('sequence_label', 'not available')}."
                    ),
                    "source_skill": skill,
                }
            )
        elif skill == "conductivity_loading":
            facts.append(
                {
                    "level": "indirect property evidence",
                    "statement": (
                        "Conductivity changes with NH3 loading within the solid-state records, "
                        "but it is measured under system-specific temperature windows and does not directly label material state."
                    ),
                    "source_skill": skill,
                }
            )
        elif skill == "h2_release_loading":
            facts.append(
                {
                    "level": "indirect property evidence",
                    "statement": (
                        "Hydrogen-release records broaden the composition–property context, "
                        "but heterogeneous conditions prevent treating the points as one continuous trend."
                    ),
                    "source_skill": skill,
                }
            )
        elif skill == "dual_axis_cross_database":
            facts.append(
                {
                    "level": "cross-database context",
                    "statement": (
                        "Conductivity and H2 release provide complementary property axes, "
                        "not direct proof of the microscopic origin of the state transition."
                    ),
                    "source_skill": skill,
                }
            )
    return facts


def _plot_evidence_map(figure_path: Path) -> None:
    fig, ax = plt.subplots(figsize=(12.0, 4.8))
    ax.axis("off")

    boxes = [
        (0.08, "State diversity\nand re-entrant sequence"),
        (0.31, "Stoichiometry alone\nis insufficient"),
        (0.54, "Cation-dependent\nlocal coordination"),
        (0.77, "Working hypothesis:\ncoordination-shell switching"),
        (0.94, "MD / MetaD\nvalidation"),
    ]

    for x, text in boxes:
        ax.text(
            x,
            0.55,
            text,
            ha="center",
            va="center",
            fontsize=12,
            bbox={"boxstyle": "round,pad=0.6", "facecolor": "white", "edgecolor": "black"},
            transform=ax.transAxes,
        )

    for (x1, _), (x2, _) in zip(boxes[:-1], boxes[1:]):
        ax.annotate(
            "",
            xy=(x2 - 0.075, 0.55),
            xytext=(x1 + 0.075, 0.55),
            xycoords=ax.transAxes,
            arrowprops={"arrowstyle": "->", "linewidth": 1.8},
        )

    ax.text(
        0.5,
        0.12,
        "Direct database evidence → constrained inference → testable microscopic hypothesis",
        ha="center",
        va="center",
        fontsize=11,
        transform=ax.transAxes,
    )
    fig.tight_layout()
    fig.savefig(figure_path, dpi=240, bbox_inches="tight")
    plt.close(fig)


class MechanismSynthesisSkill:
    name = "mechanism_synthesis"
    description = (
        "Separate direct evidence, indirect evidence, and hypotheses when comparing "
        "stoichiometry, cation effects, and coordination-shell reconstruction."
    )
    databases = ()
    produces_figure = False
    produces_table = True

    def matches(self, request: str) -> float:
        query = request.lower()
        return 8.0 if any(token in query for token in ["mechanism", "coordination-shell", "coordination shell", "hypothesis", "causal map"]) else 0.0

    def run(self, context: SkillContext) -> SkillResult:
        previous_evidence = context.parameters.get("previous_evidence", [])
        if not isinstance(previous_evidence, list):
            previous_evidence = []
        facts = _extract_previous_facts(previous_evidence)

        comparison = [
            {
                "candidate": "NH3 stoichiometry alone",
                "support": "weak",
                "assessment": (
                    "A re-entrant solid–liquid-like–solid sequence cannot be explained by a monotonic loading descriptor alone."
                ),
            },
            {
                "candidate": "cation identity and electrostatics",
                "support": "partial",
                "assessment": (
                    "Cation-dependent responses are consistent with different coordination preferences, but cation identity is not itself a microscopic descriptor."
                ),
            },
            {
                "candidate": "coordination-shell switching and framework reconstruction",
                "support": "best working hypothesis",
                "assessment": (
                    "The hypothesis directly links NH3 uptake to replacement of cation–BH4 contacts, mixed coordination near x ≈ 2, and reconstruction at higher loading."
                ),
            },
        ]

        hypothesis = {
            "statement": (
                "LiBH4·xNH3 changes state because NH3 progressively replaces BH4− in the Li+ coordination shell. "
                "Near x ≈ 2, balanced Li–N/Li–B coordination should maximize exchange and configurational disorder; "
                "at x ≈ 3, Li–N-dominant coordination should support a reconstructed solid-like network."
            ),
            "status": "testable working hypothesis",
            "required_validation": [
                "Li–N and Li–B coordination fractions",
                "coordination-mixing entropy",
                "coordination-memory decay",
                "BH4−/NH3 network renewal",
                "free-energy surfaces from metadynamics",
            ],
        }

        files: list[Path] = []
        if bool(context.parameters.get("show_figure", False)):
            context.output_dir.mkdir(parents=True, exist_ok=True)
            figure_path = context.output_dir / "skill_evidence_to_hypothesis_map.png"
            _plot_evidence_map(figure_path)
            files.append(figure_path)

        evidence = {
            "previous_evidence_available": bool(previous_evidence),
            "evidence_facts": facts,
            "candidate_comparison": comparison,
            "working_hypothesis": hypothesis,
            "actions": [
                "Reused compact structured evidence from earlier session queries when available.",
                "Separated direct database evidence from indirect property evidence and mechanistic inference.",
                "Compared stoichiometry-only, cation-effect, and coordination-shell explanations.",
                "Defined the measurements needed to test rather than merely restate the preferred hypothesis.",
            ],
            "caveats": [
                "Cross-database trends motivate the mechanism but do not prove coordination-shell switching.",
                "Microscopic validation requires structure-resolved simulation and experimental spectroscopy or scattering evidence.",
            ],
            "plot_code": inspect.getsource(_plot_evidence_map),
        }

        return SkillResult(
            skill=self.name,
            files=files,
            evidence=evidence,
            message="Synthesized an evidence-constrained mechanism comparison.",
        )
