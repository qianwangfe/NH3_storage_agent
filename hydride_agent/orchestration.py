from __future__ import annotations

import json
import os
import re
import time
from dataclasses import dataclass, field
from typing import Any

from .database_tools import DATABASE_SPECS
from .skills import build_skill_registry


@dataclass
class AgentPlan:
    databases: list[str] = field(default_factory=list)
    skill: str | None = None
    parameters: dict[str, Any] = field(default_factory=dict)
    explanation: str = ""


def _requests_figure(query: str) -> bool:
    return any(token in query for token in ["figure", "plot", "map", "diagram", "visualize"])


def _target_system(query: str) -> str:
    compact = query.replace(" ", "")
    patterns = [
        (r"mg\(bh4\)2", "Mg(BH4)2"),
        (r"libh4", "LiBH4"),
        (r"nabh4", "NaBH4"),
        (r"ca\(bh4\)2", "Ca(BH4)2"),
    ]
    for pattern, system in patterns:
        if re.search(pattern, compact, flags=re.I):
            return system
    return "LiBH4"


def deterministic_plan(request: str) -> AgentPlan:
    query = request.lower()

    if any(
        token in query
        for token in [
            "computational design",
            "molecular dynamics",
            "metadynamics",
            "uspex",
            "collective variable",
            "falsification",
            "md workflow",
        ]
    ):
        return AgentPlan(
            skill="computational_design",
            parameters={
                "use_previous_evidence": True,
                "show_figure": False,
                "show_table": True,
                "show_plot_code": False,
                "show_data_files": False,
            },
            explanation="Selected the computational validation workflow.",
        )

    if any(
        token in query
        for token in [
            "mechanism",
            "coordination-shell",
            "coordination shell",
            "hypothesis",
            "evidence-to-hypothesis",
            "causal map",
        ]
    ):
        return AgentPlan(
            skill="mechanism_synthesis",
            parameters={
                "use_previous_evidence": True,
                "show_figure": _requests_figure(query),
                "show_table": True,
                "show_plot_code": False,
                "show_data_files": True,
            },
            explanation="Selected evidence-constrained mechanism synthesis.",
        )

    has_conductivity = any(token in query for token in ["conductivity", "digbat"])
    has_hydrogen = any(token in query for token in ["h2", "hydrogen release", "dighyd", "hydrogen-storage"])
    if has_conductivity and has_hydrogen:
        return AgentPlan(
            databases=["digbat", "dighyd"],
            skill="dual_axis_cross_database",
            parameters={
                "show_figure": True,
                "show_table": True,
                "show_plot_code": False,
                "show_data_files": True,
                "include_parent": "parent" in query or "x = 0" in query,
            },
            explanation="Selected a cross-database conductivity/H2-release comparison.",
        )

    if has_conductivity:
        return AgentPlan(
            databases=["digbat"],
            skill="conductivity_loading",
            parameters={
                "show_figure": True,
                "show_table": True,
                "show_plot_code": False,
                "show_data_files": True,
                "systems": ["LiBH4", "Mg(BH4)2"],
                "temperature_windows": {
                    "LiBH4": [310.0, 3.0],
                    "Mg(BH4)2": [310.0, 3.0],
                },
            },
            explanation="Selected DOI-aware DigBat conductivity analysis.",
        )

    if has_hydrogen:
        return AgentPlan(
            databases=["dighyd"],
            skill="h2_release_loading",
            parameters={
                "show_figure": True,
                "show_table": True,
                "show_plot_code": False,
                "show_data_files": True,
                "include_parent": "parent" in query or "x = 0" in query,
                "min_ratio": 0.0,
            },
            explanation="Selected condition-aware DigHyd H2-release analysis.",
        )

    if any(
        token in query
        for token in [
            "state diversity",
            "material families",
            "family-by-state",
            "state distribution",
            "raw counts",
        ]
    ):
        return AgentPlan(
            databases=["nh3_storage"],
            skill="state_complexity",
            parameters={
                "show_figure": True,
                "show_table": True,
                "show_plot_code": False,
                "show_data_files": True,
                "include_other": False,
            },
            explanation="Selected NH3-storage family-level state statistics.",
        )

    return AgentPlan(
        databases=["nh3_storage"],
        skill="state_sequence_lookup",
        parameters={
            "target_system": _target_system(query),
            "min_ratio": 0.5,
            "max_ratio": 3.5,
            "show_figure": False,
            "show_table": True,
            "show_plot_code": False,
            "show_data_files": True,
        },
        explanation="Selected a composition-dependent state-sequence lookup.",
    )


def plan_with_llm(request: str) -> AgentPlan:
    """Use an optional OpenAI-compatible planner, with deterministic fallback."""
    provider = os.environ.get("INTENT_PROVIDER", "local").strip().lower()
    if provider != "siliconflow":
        return deterministic_plan(request)

    api_key = os.environ.get("SILICONFLOW_API_KEY", "").strip()
    if not api_key:
        return deterministic_plan(request)

    fallback = deterministic_plan(request)
    try:
        from openai import OpenAI

        registry = build_skill_registry()
        skill_names = [item["name"] for item in registry.list()]
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "create_plan",
                    "description": "Select one registered deterministic skill and its databases.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "skill": {"type": "string", "enum": skill_names},
                            "databases": {
                                "type": "array",
                                "items": {"type": "string", "enum": list(DATABASE_SPECS)},
                            },
                            "parameters": {"type": "object"},
                            "explanation": {"type": "string"},
                        },
                        "required": ["skill", "databases", "parameters"],
                    },
                },
            }
        ]

        client = OpenAI(
            api_key=api_key,
            base_url=os.environ.get("SILICONFLOW_BASE_URL", "https://api.siliconflow.cn/v1"),
            timeout=60,
            max_retries=0,
        )
        started = time.perf_counter()
        response = client.chat.completions.create(
            model=os.environ.get("INTENT_MODEL", "Qwen/Qwen2.5-7B-Instruct"),
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Route the user request to exactly one registered skill. "
                        "Use state_complexity only for family-level state counts; "
                        "state_sequence_lookup for a specific composition-dependent sequence; "
                        "conductivity_loading for DigBat; h2_release_loading for DigHyd; "
                        "dual_axis_cross_database for both; mechanism_synthesis for evidence/hypothesis comparison; "
                        "computational_design for USPEX/DFT/MD/MetaD workflows. Do not answer the science question."
                    ),
                },
                {"role": "user", "content": request},
            ],
            tools=tools,
            tool_choice={"type": "function", "function": {"name": "create_plan"}},
            temperature=0,
            max_tokens=500,
        )
        message = response.choices[0].message
        if not message.tool_calls:
            return fallback

        arguments = json.loads(message.tool_calls[0].function.arguments or "{}")
        skill = arguments.get("skill")
        if skill not in skill_names:
            return fallback
        databases = [
            database
            for database in arguments.get("databases", [])
            if database in DATABASE_SPECS
        ]
        parameters = arguments.get("parameters") if isinstance(arguments.get("parameters"), dict) else {}
        merged_parameters = dict(fallback.parameters)
        merged_parameters.update(parameters)
        elapsed = time.perf_counter() - started
        return AgentPlan(
            databases=databases or fallback.databases,
            skill=skill,
            parameters=merged_parameters,
            explanation=arguments.get("explanation") or f"LLM routing completed in {elapsed:.2f} s.",
        )
    except Exception as exc:
        print(f"[Agent] Planner failed; using deterministic routing: {type(exc).__name__}: {exc}")
        return fallback
