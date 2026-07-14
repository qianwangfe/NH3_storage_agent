from __future__ import annotations

import json
import os
from typing import Any


def synthesize(question: str, evidence: dict[str, Any]) -> str | None:
    """Optionally synthesize a concise conclusion from structured evidence only."""
    provider = os.environ.get("SYNTHESIS_PROVIDER", "local").strip().lower()
    if provider == "local":
        return None

    prompt = (
        "Use only the structured evidence below. Do not invent materials, values, DOI, "
        "coordination numbers, or mechanisms. Distinguish direct evidence from inference. "
        "Keep the conclusion under 120 words.\n\n"
        f"Question:\n{question}\n\n"
        f"Evidence:\n{json.dumps(evidence, ensure_ascii=False, indent=2, default=str)}"
    )

    if provider == "gemini":
        from google import genai

        key = os.environ.get("GEMINI_API_KEY", "").strip()
        if not key:
            return None
        client = genai.Client(api_key=key)
        response = client.models.generate_content(
            model=os.environ.get("SYNTHESIS_MODEL", "gemini-2.5-flash"),
            contents=prompt,
        )
        return str(response.text).strip() if response.text else None

    if provider == "siliconflow":
        from openai import OpenAI

        key = os.environ.get("SILICONFLOW_API_KEY", "").strip()
        if not key:
            return None
        client = OpenAI(
            api_key=key,
            base_url=os.environ.get("SILICONFLOW_BASE_URL", "https://api.siliconflow.cn/v1"),
            timeout=60,
            max_retries=0,
        )
        response = client.chat.completions.create(
            model=os.environ.get("SYNTHESIS_MODEL", "Qwen/Qwen2.5-7B-Instruct"),
            messages=[
                {"role": "system", "content": "You are an evidence-constrained scientific synthesis assistant."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
            max_tokens=300,
        )
        return response.choices[0].message.content

    return None
