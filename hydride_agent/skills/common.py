from __future__ import annotations

import re
from typing import Iterable

import numpy as np
import pandas as pd

_SUBSCRIPT_TRANSLATION = str.maketrans("₀₁₂₃₄₅₆₇₈₉", "0123456789")
_PHASE_MARKERS = re.compile(r"\((?:s|l|g|aq|solid|liquid)\)", re.I)


def clean_formula(value: object) -> str:
    text = str(value or "").translate(_SUBSCRIPT_TRANSLATION)
    text = text.replace("∙", "·").replace("⋅", "·").replace("–", "-")
    text = _PHASE_MARKERS.sub("", text)
    return re.sub(r"\s+", "", text)


def choose_column(frame: pd.DataFrame, candidates: Iterable[str]) -> str | None:
    exact = {str(column).strip().lower(): str(column) for column in frame.columns}
    for candidate in candidates:
        key = candidate.strip().lower()
        if key in exact:
            return exact[key]

    for column in frame.columns:
        normalized = str(column).strip().lower()
        if any(candidate.strip().lower() in normalized for candidate in candidates):
            return str(column)
    return None


def host_system_base(formula: object) -> str:
    text = clean_formula(formula)
    text = re.sub(r"(?:[·-](?:\d+(?:\.\d+)?)?NH3)+$", "", text, flags=re.I)
    text = re.sub(r"(?:\(NH3\)(?:\d+(?:\.\d+)?)?)+$", "", text, flags=re.I)

    grouped = re.match(r"^([A-Z][a-z]?(?:\d+(?:\.\d+)?)?\(BH4\)(?:\d+(?:\.\d+)?)?)", text)
    if grouped:
        return grouped.group(1)

    simple = re.match(r"^([A-Z][a-z]?(?:\d+(?:\.\d+)?)?BH4)", text)
    if simple:
        return simple.group(1)

    return text


def _count_group(text: str, group: str) -> float:
    total = 0.0
    pattern = rf"\({re.escape(group)}\)(\d+(?:\.\d+)?)?"
    for match in re.finditer(pattern, text, flags=re.I):
        total += float(match.group(1)) if match.group(1) else 1.0
    return total


def nh3_per_bh4(formula: object) -> float:
    text = clean_formula(formula)

    n_bh4 = _count_group(text, "BH4")
    without_grouped_bh4 = re.sub(
        r"\(BH4\)(?:\d+(?:\.\d+)?)?", "", text, flags=re.I
    )
    n_bh4 += float(len(re.findall(r"BH4", without_grouped_bh4, flags=re.I)))

    n_nh3 = _count_group(text, "NH3")
    without_grouped_nh3 = re.sub(
        r"\(NH3\)(?:\d+(?:\.\d+)?)?", "", text, flags=re.I
    )
    for match in re.finditer(
        r"[·-](?:(\d+(?:\.\d+)?)?)NH3", without_grouped_nh3, flags=re.I
    ):
        n_nh3 += float(match.group(1)) if match.group(1) else 1.0

    return n_nh3 / n_bh4 if n_bh4 else np.nan


def pure_parent_or_ammine(formula: object) -> bool:
    text = clean_formula(formula)
    excluded = [
        r"NH3BH3",
        r"THF",
        r"H2O",
        r"Al2O3",
        r"MgO",
        r"TiO2",
        r"LiH",
        r"ZnCl2",
        r"CoCl2",
        r"NiCl2",
        r"FeCl3",
        r"/",
        r"@",
        r"\+",
    ]
    if any(re.search(pattern, text, flags=re.I) for pattern in excluded):
        return False

    host = r"(?:[A-Z][a-z]?(?:\d+(?:\.\d+)?)?)+(?:\(BH4\)(?:\d+(?:\.\d+)?)?|BH4)"
    ammine = r"(?:(?:[·-](?:\d+(?:\.\d+)?)?NH3)|(?:\(NH3\)(?:\d+(?:\.\d+)?)?))*"
    return bool(re.fullmatch(host + ammine, text, flags=re.I))


def normalize_state(value: object) -> str:
    text = str(value or "").strip().lower()
    if not text or text in {"nan", "none", "unknown", "not reported", "—"}:
        return "not reported"
    if "liquid" in text and any(
        token in text for token in ["solid", "pseudo", "partial", "transition"]
    ):
        return "mixed/transition"
    if any(token in text for token in ["melt", "transition", "mixed", "gel", "pseudo"]):
        return "mixed/transition"
    if "liquid" in text:
        return "liquid"
    if any(token in text for token in ["solid", "powder", "crystal", "rigid"]):
        return "solid"
    return "not reported"


def family_from_text(value: object) -> str:
    text = str(value or "").lower()
    if "ammonia borane" in text or "nh3bh3" in text:
        return "ammine-borane"
    if "borohydride" in text or "bh4" in text:
        return "borohydride"
    if "halide" in text or any(token in text for token in ["chloride", "bromide", "iodide", "fluoride"]):
        return "halide"
    return "other"


def safe_text(value: object, default: str = "—") -> str:
    if value is None:
        return default
    try:
        if pd.isna(value):
            return default
    except Exception:
        pass
    text = str(value).strip()
    return text if text and text.lower() != "nan" else default


def join_nonempty(values: Iterable[object], separator: str = "; ") -> str:
    cleaned = [safe_text(value, "") for value in values]
    cleaned = [value for value in cleaned if value]
    return separator.join(cleaned) if cleaned else "—"
