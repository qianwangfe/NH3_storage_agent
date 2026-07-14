from __future__ import annotations

import shutil
from pathlib import Path

from hydride_agent.agent import clear_session, run_agent
from hydride_agent.config import PROJECT_ROOT, RAW_DIR

QUERIES = [
    (
        "01_state_diversity",
        "Using the NH3 Storage dataset, compare the raw counts of solid, mixed/transition, and liquid records across material families. Highlight borohydrides and return the figure and supporting CSV files.",
    ),
    (
        "02_state_sequence",
        "Trace the reported state sequence of LiBH4·xNH3 from x = 1 to 3. List the composition, reported state, conditions, evidence type, confidence, and DOI. Determine whether the literature supports a solid–liquid-like–solid sequence.",
    ),
    (
        "03_conductivity",
        "Using DigBat, plot ionic conductivity against NH3/BH4 ratio for LiBH4 near 305 ± 3 K and Mg(BH4)2 near 323 ± 3 K. Use one representative value per formula and DOI, aggregate multiple DOI in log10 conductivity space, and export the plotting data.",
    ),
    (
        "04_h2_release",
        "Using DigHyd, compare reported H2 release across ammoniated borohydrides with NH3/BH4 > 0. Retain the host borohydride, loading, temperature, conditions, and DOI. Do not connect non-comparable studies.",
    ),
    (
        "05_mechanism_map",
        "Based on the previous state, conductivity, and H2-release evidence, compare NH3 stoichiometry alone, cation effects, and coordination-shell reconstruction. Separate direct evidence, indirect evidence, and hypotheses, and generate an evidence-to-hypothesis map.",
    ),
    (
        "06_computational_design",
        "Design a USPEX, molecular-dynamics, and metadynamics workflow to test whether coordination-shell switching explains LiBH4·NH3, LiBH4·2NH3, and LiBH4·3NH3. Specify collective variables, descriptors, expected observations, uncertainty checks, and falsification criteria.",
    ),
]


def main() -> None:
    session_id = "reproduction-session"
    clear_session(session_id)
    output_root = PROJECT_ROOT / "outputs" / "reproduction"
    run_dir = output_root / "runtime"
    if output_root.exists():
        shutil.rmtree(output_root)
    run_dir.mkdir(parents=True, exist_ok=True)

    index_lines = ["# Reproduced agent outputs", "", f"Data directory: `{RAW_DIR}`", ""]
    for label, query in QUERIES:
        query_dir = output_root / label
        query_dir.mkdir(parents=True, exist_ok=True)
        result = run_agent(query, session_id=session_id, raw_dir=RAW_DIR, out_dir=run_dir)
        report_path = query_dir / "report.md"
        report_path.write_text(result.answer, encoding="utf-8")

        copied = []
        for artifact in result.files:
            source = Path(artifact)
            destination = query_dir / source.name
            shutil.copy2(source, destination)
            copied.append(destination.name)

        index_lines.extend(
            [
                f"## {label}",
                "",
                query,
                "",
                f"- Skill: `{result.plan.get('skill')}`",
                f"- Report: `{report_path.relative_to(output_root)}`",
                *[f"- Artifact: `{label}/{name}`" for name in copied],
                "",
            ]
        )

    (output_root / "README.md").write_text("\n".join(index_lines), encoding="utf-8")
    print(f"Reproduction outputs written to {output_root}")


if __name__ == "__main__":
    main()
