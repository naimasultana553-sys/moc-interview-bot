"""Thin OpenAI client wrapper with graceful offline handling."""
from __future__ import annotations

import json
import re
from typing import Any

from app.config import get_settings


def _extract_json(content: str) -> Any:
    content = (content or "").strip()
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{.*\}", content, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass
    match = re.search(r"\[.*\]", content, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass
    raise ValueError(f"Could not parse model JSON output: {content[:300]}")


class AIClient:
    def __init__(self) -> None:
        self.settings = get_settings()
        self._client = None
        if self.settings.openai_api_key.strip():
            from openai import OpenAI

            self._client = OpenAI(api_key=self.settings.openai_api_key)

    @property
    def available(self) -> bool:
        return self._client is not None

    def chat_json(self, system: str, user: str, temperature: float = 0.7) -> Any:
        if not self._client:
            raise RuntimeError("OpenAI client not configured")
        resp = self._client.chat.completions.create(
            model=self.settings.openai_model,
            response_format={"type": "json_object"},
            temperature=temperature,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        content = resp.choices[0].message.content
        return _extract_json(content)
