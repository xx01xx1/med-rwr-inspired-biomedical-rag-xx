from __future__ import annotations

import json
import os
import re
from typing import Any

from openai import OpenAI

from src.confidence import estimate_confidence
from src.prompts import SYSTEM_PROMPT


def _extract_json(text: str) -> dict[str, Any]:
    """Parse strict JSON, with a small fallback for fenced model output."""
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            raise
        return json.loads(match.group(0))


def call_openai_json(prompt: str, model: str | None = None) -> dict[str, Any]:
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is missing.")

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    response = client.chat.completions.create(
        model=model or os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
        response_format={"type": "json_object"},
    )
    content = response.choices[0].message.content or "{}"
    return _extract_json(content)


def normalize_candidate_confidence(result: dict[str, Any]) -> dict[str, Any]:
    """Ensure every candidate has a confidence label even if the model omits it."""
    for candidate in result.get("candidates", []) or []:
        current = candidate.get("confidence")
        if current not in {"High", "Medium", "Low"}:
            candidate["confidence"] = estimate_confidence(candidate)
    return result


def rank_targets(prompt: str) -> dict[str, Any]:
    result = call_openai_json(prompt)
    return normalize_candidate_confidence(result)
