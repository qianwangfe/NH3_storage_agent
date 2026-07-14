from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol


@dataclass
class SkillContext:
    raw_dir: Path
    output_dir: Path
    user_request: str
    parameters: dict[str, Any] = field(default_factory=dict)


@dataclass
class SkillResult:
    skill: str
    files: list[Path] = field(default_factory=list)
    evidence: dict[str, Any] = field(default_factory=dict)
    message: str = ""


class AnalysisSkill(Protocol):
    name: str
    description: str
    databases: tuple[str, ...]
    produces_figure: bool
    produces_table: bool

    def matches(self, request: str) -> float: ...
    def run(self, context: SkillContext) -> SkillResult: ...


class SkillRegistry:
    def __init__(self) -> None:
        self._skills: dict[str, AnalysisSkill] = {}

    def register(self, skill: AnalysisSkill) -> None:
        self._skills[skill.name] = skill

    def get(self, name: str | None) -> AnalysisSkill:
        if not name:
            raise KeyError("No skill was selected.")
        if name not in self._skills:
            raise KeyError(f"Unknown skill: {name}")
        return self._skills[name]

    def list(self) -> list[dict[str, Any]]:
        return [
            {
                "name": skill.name,
                "description": skill.description,
                "databases": list(skill.databases),
                "produces_figure": bool(skill.produces_figure),
                "produces_table": bool(skill.produces_table),
            }
            for skill in self._skills.values()
        ]
