from __future__ import annotations

import os
from typing import Any, Dict

import requests
from mcp.server.fastmcp import FastMCP


MCP_AGENT_GUIDANCE = """
MCP tools for the Hydride NH3 Complete Private agent.

This version targets the v0.2 skill-based FastAPI backend:
- GET  /databases
- GET  /skills
- POST /chat
- POST /skills/{skill_name}

Start the backend first:
python -m uvicorn hydride_agent.api:app --host 127.0.0.1 --port 8520 --reload
"""

try:
    mcp = FastMCP("hydride-agent", instructions=MCP_AGENT_GUIDANCE)
except TypeError:
    mcp = FastMCP("hydride-agent")

BASE_URL = os.environ.get("HYDRIDE_API_URL", "http://127.0.0.1:8520").rstrip("/")


def _request_json(
    method: str,
    endpoint: str,
    *,
    params: dict | None = None,
    json_body: dict | None = None,
    timeout: int = 60,
) -> Dict[str, Any]:
    url = f"{BASE_URL}{endpoint}"
    try:
        r = requests.request(method, url, params=params, json=json_body, timeout=timeout)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.ConnectionError:
        return {
            "success": False,
            "error_type": "connection_error",
            "message": f"Could not connect to Hydride backend at {BASE_URL}. Start uvicorn first.",
            "endpoint": endpoint,
            "method": method,
        }
    except requests.exceptions.Timeout:
        return {
            "success": False,
            "error_type": "timeout",
            "message": f"Backend request timed out after {timeout} seconds.",
            "endpoint": endpoint,
            "method": method,
        }
    except requests.exceptions.HTTPError as e:
        return {
            "success": False,
            "error_type": "http_error",
            "message": str(e),
            "status_code": getattr(e.response, "status_code", None),
            "endpoint": endpoint,
            "method": method,
            "response_text": getattr(e.response, "text", ""),
        }
    except ValueError:
        return {
            "success": False,
            "error_type": "json_decode_error",
            "message": "Backend response was not valid JSON.",
            "endpoint": endpoint,
            "method": method,
            "response_text": r.text if "r" in locals() else "",
        }
    except Exception as e:
        return {
            "success": False,
            "error_type": "unexpected_error",
            "message": str(e),
            "endpoint": endpoint,
            "method": method,
        }


@mcp.tool()
def list_databases() -> dict:
    """List databases known to the Hydride NH3 agent."""
    return {"success": True, "databases": _request_json("GET", "/databases", timeout=30)}


@mcp.tool()
def list_skills() -> dict:
    """List available deterministic analysis skills in the v0.2 backend."""
    return {"success": True, "skills": _request_json("GET", "/skills", timeout=30)}


@mcp.tool()
def run_skill(skill_name: str, parameters: dict | None = None) -> dict:
    """
    Run one deterministic skill by name.

    Useful skill names in Complete Private normally include:
    - state_complexity
    - state_sequence_lookup
    - conductivity_loading
    - h2_release_loading
    - dual_axis_cross_database
    - mechanism_synthesis
    - computational_design

    Example parameters:
    {"target_system": "LiBH4"}
    """
    return _request_json(
        "POST",
        f"/skills/{skill_name}",
        json_body=parameters or {},
        timeout=90,
    )


@mcp.tool()
def answer_question(question: str, session_id: str | None = None) -> dict:
    """
    Ask the v0.2 Hydride NH3 agent a natural-language question via POST /chat.

    Use this for open-ended mechanism questions, material comparisons, or cases
    where routing to a specific deterministic skill is not obvious.
    """
    return _request_json(
        "POST",
        "/chat",
        json_body={"message": question, "session_id": session_id},
        timeout=120,
    )


@mcp.tool()
def state_sequence_lookup(target_system: str = "LiBH4") -> dict:
    """
    Convenience wrapper for the state_sequence_lookup skill.
    Use for LiBH4·xNH3 style non-monotonic solid/liquid/solid sequence questions.
    """
    return run_skill("state_sequence_lookup", {"target_system": target_system})


@mcp.tool()
def state_complexity() -> dict:
    """
    Convenience wrapper for reported physical-state diversity by material family.
    """
    return run_skill("state_complexity", {})


if __name__ == "__main__":
    mcp.run()
