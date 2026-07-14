from __future__ import annotations

from .base import SkillContext, SkillResult


class ComputationalDesignSkill:
    name = "computational_design"
    description = (
        "Design an article-aligned USPEX/DFT/MD/MetaD workflow to test "
        "coordination-shell switching in LiBH4·xNH3."
    )
    databases = ()
    produces_figure = False
    produces_table = True

    def matches(self, request: str) -> float:
        query = request.lower()
        keywords = [
            "computational design",
            "molecular dynamics",
            "metadynamics",
            "uspex",
            "collective variable",
            "falsification",
            "md workflow",
        ]
        return 9.0 if any(keyword in query for keyword in keywords) else 0.0

    def run(self, context: SkillContext) -> SkillResult:
        previous_evidence = context.parameters.get("previous_evidence", [])
        if not isinstance(previous_evidence, list):
            previous_evidence = []

        systems = [
            {"formula": "LiBH4·NH3", "role": "solid reference at x = 1"},
            {"formula": "LiBH4·2NH3", "role": "liquid-like or mixed reference near x = 2"},
            {"formula": "LiBH4·3NH3", "role": "reconstructed solid-like reference at x = 3"},
        ]

        workflow = [
            {
                "stage": "Structure preparation",
                "tasks": [
                    "Generate low-energy x = 1–3 structures; use evolutionary structure search for unresolved compositions when needed.",
                    "Relax structures and cells with dispersion-aware DFT and verify the absence of unstable modes or obvious decomposition artifacts.",
                ],
            },
            {
                "stage": "Unbiased molecular dynamics",
                "tasks": [
                    "Run multiple independent trajectories at the experimentally relevant temperature range.",
                    "Check equilibration, energy drift, density stability, and finite-size effects before interpreting state behavior.",
                ],
            },
            {
                "stage": "Coordination descriptors",
                "tasks": [
                    "Calculate Li–N and Li–B coordination fractions using RDF-derived cutoffs.",
                    "Calculate coordination-mixing entropy or an equivalent mixed-shell index.",
                    "Measure coordination-memory decay and Li-shell exchange rates.",
                    "Track N···B neighbor counts, BH4−/NH3 network renewal, and relevant RDFs.",
                ],
            },
            {
                "stage": "Metadynamics",
                "tasks": [
                    "Use Li–N and Li–B coordination numbers as collective variables.",
                    "Reconstruct free-energy surfaces and compare basin breadth, barriers, and reversibility across x = 1–3.",
                    "Verify that conclusions are robust to CV definitions, Gaussian parameters, and trajectory length.",
                ],
            },
            {
                "stage": "Cross-validation",
                "tasks": [
                    "Compare simulated mobility and local structure with PCT, 1H NMR, Raman, or other available experimental signatures.",
                    "Report uncertainty across trajectories and avoid assigning bulk phase solely from a single short simulation.",
                ],
            },
        ]

        expected_observations = [
            {
                "system": "LiBH4·NH3",
                "expected": "More persistent Li–B framework contacts, lower mixed-shell entropy, and longer coordination memory.",
            },
            {
                "system": "LiBH4·2NH3",
                "expected": "Comparable Li–N and Li–B fractions, maximal mixed-shell entropy, faster shell exchange, and a broader free-energy landscape.",
            },
            {
                "system": "LiBH4·3NH3",
                "expected": "Li–N-dominant coordination with a reconstructed, slower-renewing network and renewed solid-like persistence.",
            },
        ]

        falsification_criteria = [
            "Li–N/Li–B fractions remain nearly identical across x = 1–3.",
            "LiBH4·2NH3 does not show faster coordination exchange, weaker memory, or a broader free-energy landscape than x = 1 and 3.",
            "The state ordering changes when reasonable RDF cutoffs, cell sizes, or independent initial structures are used.",
            "The proposed coordination descriptors fail to correlate with experimental mobility or state-sensitive measurements.",
        ]

        evidence = {
            "previous_evidence_available": bool(previous_evidence),
            "target_systems": systems,
            "workflow": workflow,
            "expected_observations": expected_observations,
            "falsification_criteria": falsification_criteria,
            "minimum_reporting": [
                "cell size and composition",
                "DFT functional and dispersion treatment",
                "time step, thermostat/barostat, equilibration, and production length",
                "RDF cutoffs and sensitivity analysis",
                "MetaD CV definitions and bias parameters",
                "independent trajectories and uncertainty",
            ],
            "actions": [
                "Converted the coordination-shell hypothesis into measurable descriptors.",
                "Separated unbiased dynamics from biased free-energy sampling.",
                "Specified expected outcomes for x = 1, 2, and 3.",
                "Defined explicit falsification criteria and reporting requirements.",
            ],
        }

        return SkillResult(
            skill=self.name,
            files=[],
            evidence=evidence,
            message="Designed an article-aligned computational validation workflow.",
        )
