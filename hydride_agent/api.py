from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

from .agent import run_agent
from .config import OUTPUT_DIR, RAW_DIR
from .database_tools import DatabaseRouter
from .models import ChatRequest, ChatResponse
from .skills import build_skill_registry
from .skills.base import SkillContext

app = FastAPI(
    title="NH3 Storage Agent API",
    description="Tool-gated analysis of NH3 Storage, DigBat, and DigHyd records.",
    version="0.2.0",
)


@app.get("/")
def root() -> dict:
    return {
        "name": "NH3 Storage Agent API",
        "status": "ok",
        "data_directory": str(RAW_DIR),
        "endpoints": ["/databases", "/skills", "/chat", "/skills/{skill_name}"],
    }


@app.get("/databases")
def databases() -> list[dict[str, str]]:
    return DatabaseRouter().list_databases()


@app.get("/skills")
def skills() -> list[dict]:
    return build_skill_registry().list()


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    result = run_agent(request.message, session_id=request.session_id)
    return ChatResponse(answer=result.answer, files=result.files, plan=result.plan)


@app.post("/skills/{skill_name}")
def run_skill(skill_name: str, parameters: dict | None = None) -> dict:
    registry = build_skill_registry()
    try:
        skill = registry.get(skill_name)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    context = SkillContext(
        raw_dir=RAW_DIR,
        output_dir=OUTPUT_DIR,
        user_request=f"Run {skill_name}",
        parameters=parameters or {},
    )
    result = skill.run(context)
    return {
        "skill": result.skill,
        "message": result.message,
        "files": [str(path) for path in result.files],
        "evidence": result.evidence,
    }


@app.get("/download/{filename}")
def download(filename: str) -> FileResponse:
    path = (Path(OUTPUT_DIR) / filename).resolve()
    output_root = Path(OUTPUT_DIR).resolve()
    if output_root not in path.parents or not path.exists() or not path.is_file():
        raise HTTPException(status_code=404, detail="File not found.")
    return FileResponse(path)
