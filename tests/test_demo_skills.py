from pathlib import Path

from hydride_agent.agent import clear_session, run_agent
from hydride_agent.skills import build_skill_registry


def test_skill_catalog_contains_all_seven_skills():
    names = {item["name"] for item in build_skill_registry().list()}
    assert names == {
        "state_complexity",
        "state_sequence_lookup",
        "conductivity_loading",
        "h2_release_loading",
        "dual_axis_cross_database",
        "mechanism_synthesis",
        "computational_design",
    }


def test_database_skills_run_on_demo_data(demo_dir: Path, tmp_path: Path):
    queries = [
        "Compare state diversity across material families",
        "Trace the LiBH4 state sequence from x = 1 to 3",
        "Plot DigBat conductivity against NH3/BH4",
        "Compare DigHyd H2 release for ammoniated borohydrides",
        "Compare DigBat conductivity and DigHyd H2 release",
    ]
    for query in queries:
        result = run_agent(query, session_id="test-session", raw_dir=demo_dir, out_dir=tmp_path)
        assert result.answer
        assert result.data_preview == []
        for path in result.files:
            assert Path(path).exists()


def test_mechanism_reuses_session_evidence(demo_dir: Path, tmp_path: Path):
    session_id = "mechanism-test"
    clear_session(session_id)
    run_agent("Compare state diversity across material families", session_id, demo_dir, tmp_path)
    run_agent("Trace the LiBH4 state sequence from x = 1 to 3", session_id, demo_dir, tmp_path)
    result = run_agent(
        "Compare the mechanism hypotheses and generate an evidence-to-hypothesis map",
        session_id,
        demo_dir,
        tmp_path,
    )
    assert result.evidence["previous_evidence_available"] is True
    assert any(Path(path).suffix == ".png" for path in result.files)
