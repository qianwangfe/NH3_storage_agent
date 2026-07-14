from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from .config import DATABASE_FILES, OUTPUT_DIR, RAW_DIR


@dataclass(frozen=True)
class DatabaseSpec:
    key: str
    label: str
    filename: str
    role: str
    sheet: str | int


DATABASE_SPECS: dict[str, DatabaseSpec] = {
    "nh3_storage": DatabaseSpec(
        key="nh3_storage",
        label="NH3 Storage",
        filename=DATABASE_FILES["nh3_storage"],
        sheet="All_Proposed_Records",
        role=(
            "Reported NH3 uptake, material state, phase behavior, "
            "experimental conditions, and literature provenance."
        ),
    ),
    "digbat": DatabaseSpec(
        key="digbat",
        label="DigBat",
        filename=DATABASE_FILES["digbat"],
        sheet="Sheet1",
        role=(
            "Solid-electrolyte conductivity, temperature, activation energy, "
            "composition, and DOI records."
        ),
    ),
    "dighyd": DatabaseSpec(
        key="dighyd",
        label="DigHyd",
        filename=DATABASE_FILES["dighyd"],
        sheet="Sheet1",
        role=(
            "Hydrogen-release or storage properties, test conditions, "
            "composition, and DOI records."
        ),
    ),
}


def _clean_jsonable(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _clean_jsonable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_clean_jsonable(item) for item in value]
    try:
        if pd.isna(value):
            return None
    except Exception:
        pass
    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            pass
    return value


class DatabaseRouter:
    """Read-only access to the three registered scientific backends."""

    def __init__(self, raw_dir: Path = RAW_DIR, output_dir: Path = OUTPUT_DIR):
        self.raw_dir = Path(raw_dir)
        self.output_dir = Path(output_dir)
        self._cache: dict[str, pd.DataFrame] = {}

    def list_databases(self) -> list[dict[str, str]]:
        return [
            {
                "key": spec.key,
                "label": spec.label,
                "filename": spec.filename,
                "role": spec.role,
            }
            for spec in DATABASE_SPECS.values()
        ]

    def path_for(self, database: str) -> Path:
        if database not in DATABASE_SPECS:
            raise KeyError(f"Unknown database: {database}")
        return self.raw_dir / DATABASE_SPECS[database].filename

    def load(self, database: str) -> pd.DataFrame:
        if database not in DATABASE_SPECS:
            raise KeyError(f"Unknown database: {database}")
        if database in self._cache:
            return self._cache[database].copy()

        spec = DATABASE_SPECS[database]
        path = self.path_for(database)
        if not path.exists():
            raise FileNotFoundError(
                f"Missing {spec.filename} in {self.raw_dir}. "
                "Set HYDRIDE_AGENT_DATA_DIR or copy the required workbooks."
            )

        frame = pd.read_excel(path, sheet_name=spec.sheet)
        self._cache[database] = frame
        return frame.copy()

    def query(
        self,
        database: str,
        *,
        formula: str | None = None,
        keywords: list[str] | None = None,
        columns: list[str] | None = None,
        limit: int = 50,
    ) -> dict[str, Any]:
        frame = self.load(database)
        mask = pd.Series(True, index=frame.index)
        searchable = frame.astype(str).agg(" | ".join, axis=1)

        if formula:
            token = re.sub(r"\s+", "", str(formula)).lower()
            normalized = searchable.str.replace(" ", "", regex=False).str.lower()
            mask &= normalized.str.contains(re.escape(token), na=False)

        for keyword in keywords or []:
            mask &= searchable.str.contains(
                re.escape(str(keyword)), case=False, na=False
            )

        result = frame.loc[mask].copy()
        if columns:
            keep = [column for column in columns if column in result.columns]
            result = result[keep]

        total = int(len(result))
        preview = result.head(max(0, min(limit, 200)))
        return {
            "database": database,
            "role": DATABASE_SPECS[database].role,
            "matched_records": total,
            "columns": list(result.columns),
            "records": _clean_jsonable(preview.to_dict(orient="records")),
            "truncated": total > len(preview),
        }

    def export_csv(self, frame: pd.DataFrame, filename: str) -> Path:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        safe_name = re.sub(r"[^A-Za-z0-9_.-]+", "_", filename)
        path = self.output_dir / safe_name
        frame.to_csv(path, index=False, encoding="utf-8-sig")
        return path
