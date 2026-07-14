from __future__ import annotations

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

DATABASE_FILES = {
    "nh3_storage": os.environ.get(
        "NH3_STORAGE_FILE",
        "NH3_storage_data_codex_verified_summary_after_batch_03.xlsx",
    ),
    "digbat": os.environ.get(
        "DIGBAT_FILE",
        "Digbat_V114_Hydride.xlsx",
    ),
    "dighyd": os.environ.get(
        "DIGHYD_FILE",
        "DigHyd_database.xlsx",
    ),
}


def _contains_required_files(directory: Path) -> bool:
    return all((directory / filename).exists() for filename in DATABASE_FILES.values())


def resolve_data_dir() -> Path:
    configured = os.environ.get("HYDRIDE_AGENT_DATA_DIR", "").strip()
    if configured:
        return Path(configured).expanduser().resolve()

    private_dir = PROJECT_ROOT / "data" / "raw"
    if _contains_required_files(private_dir):
        return private_dir

    return PROJECT_ROOT / "data" / "demo"


RAW_DIR = resolve_data_dir()
OUTPUT_DIR = Path(
    os.environ.get("HYDRIDE_AGENT_OUTPUT_DIR", PROJECT_ROOT / "outputs")
).expanduser().resolve()
