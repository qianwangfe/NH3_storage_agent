from pathlib import Path

from hydride_agent.agent import run_agent


def test_frontend_does_not_expose_raw_preview(demo_dir: Path, tmp_path: Path):
    result = run_agent("Plot DigBat conductivity", raw_dir=demo_dir, out_dir=tmp_path)
    assert result.data_preview == []
    assert "database_coverage" in result.evidence
