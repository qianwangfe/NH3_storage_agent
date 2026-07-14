from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class AgentResult(BaseModel):
    answer: str
    files: list[str] = Field(default_factory=list)
    data_preview: list[dict[str, Any]] = Field(default_factory=list)
    plan: dict[str, Any] = Field(default_factory=dict)
    evidence: dict[str, Any] = Field(default_factory=dict)


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None


class ChatResponse(BaseModel):
    answer: str
    files: list[str] = Field(default_factory=list)
    plan: dict[str, Any] = Field(default_factory=dict)
