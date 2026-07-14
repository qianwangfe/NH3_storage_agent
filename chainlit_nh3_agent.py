from __future__ import annotations

import asyncio
import re
import shutil
import traceback
import uuid
from pathlib import Path
from typing import Any, Iterable

import chainlit as cl

ROOT = Path(__file__).resolve().parent
PUBLIC_GENERATED = ROOT / "public" / "generated"
PUBLIC_GENERATED.mkdir(parents=True, exist_ok=True)
SECTION_DELAY_SECONDS = 0.2
MAX_ANSWER_SECTIONS = 10
MAJOR_SECTION_PATTERN = re.compile(r"(?=^##\s+)", flags=re.MULTILINE)


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, (str, Path, dict)):
        return [value]
    if isinstance(value, Iterable):
        return list(value)
    return [value]


def collect_artifacts(result: Any) -> list[Any]:
    values = _as_list(getattr(result, "files", []))
    unique: list[Any] = []
    seen: set[str] = set()
    for value in values:
        key = str(value)
        if key not in seen:
            seen.add(key)
            unique.append(value)
    return unique


def resolve_artifact_path(value: Any) -> Path | None:
    path = Path(str(value)).expanduser()
    if not path.is_absolute():
        path = ROOT / path
    try:
        path = path.resolve()
    except OSError:
        return None
    return path if path.exists() and path.is_file() else None


def publish_artifact(source: Path) -> tuple[Path, str]:
    destination = PUBLIC_GENERATED / f"{uuid.uuid4().hex[:10]}_{source.name}"
    shutil.copy2(source, destination)
    return destination, f"/public/generated/{destination.name}"


def split_answer_sections(answer: str) -> list[str]:
    sections = [section.strip() for section in MAJOR_SECTION_PATTERN.split(str(answer or "")) if section.strip()]
    if len(sections) <= MAX_ANSWER_SECTIONS:
        return sections
    return sections[: MAX_ANSWER_SECTIONS - 1] + ["\n\n".join(sections[MAX_ANSWER_SECTIONS - 1 :])]


async def send_answer_progressively(answer: str) -> None:
    sections = split_answer_sections(answer)
    for index, section in enumerate(sections):
        await cl.Message(content=section, author="NH3 Storage Agent").send()
        if index < len(sections) - 1:
            await asyncio.sleep(SECTION_DELAY_SECONDS)


async def send_artifacts(result: Any) -> None:
    image_suffixes = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"}
    for raw_artifact in collect_artifacts(result):
        source = resolve_artifact_path(raw_artifact)
        if source is None:
            continue
        _, public_url = publish_artifact(source)
        if source.suffix.lower() in image_suffixes:
            content = f"### Generated figure\n\n![{source.stem}]({public_url})\n\n[Open full-size image]({public_url})"
        else:
            content = f"### Generated file\n\n[Download {source.name}]({public_url})"
        await cl.Message(content=content, author="NH3 Storage Agent").send()
        await asyncio.sleep(SECTION_DELAY_SECONDS)


@cl.on_chat_start
async def on_chat_start() -> None:
    cl.user_session.set("question_count", 0)
    await cl.Message(
        content=(
            "**NH₃ Storage Agent is ready.**\n\n"
            "Explore reported material states, ionic conductivity, hydrogen release, "
            "and coordination mechanisms across the NH₃ Storage, DigBat, and DigHyd datasets. "
            "Each query is processed by a registered deterministic skill and returned with traceable evidence and artifacts."
        ),
        author="NH3 Storage Agent",
    ).send()


@cl.on_message
async def on_message(message: cl.Message) -> None:
    user_text = str(message.content or "").strip()
    if not user_text:
        await cl.Message(content="Please enter a question.", author="NH3 Storage Agent").send()
        return

    try:
        from hydride_agent.agent import run_agent

        session_id = str(cl.user_session.get("id") or "chainlit-session")
        async with cl.Step(name="1. Request interpretation", type="tool") as step:
            step.input = user_text
            step.output = "Selecting the required database tools and deterministic skill."

        async with cl.Step(name="2. Database and skill execution", type="tool") as step:
            result = await asyncio.to_thread(run_agent, user_text, session_id)
            step.output = f"Execution completed. Generated artifacts: {len(collect_artifacts(result))}."

        async with cl.Step(name="3. Evidence synthesis", type="tool") as step:
            step.output = f"Prepared {len(split_answer_sections(result.answer))} public report sections."

        await send_answer_progressively(result.answer)
        if collect_artifacts(result):
            async with cl.Step(name="4. Artifact publication", type="tool") as step:
                await send_artifacts(result)
                step.output = "Artifacts published."
    except Exception as exc:
        traceback.print_exc()
        await cl.Message(
            content=f"Agent execution failed.\n\n`{type(exc).__name__}: {exc}`",
            author="NH3 Storage Agent",
        ).send()
