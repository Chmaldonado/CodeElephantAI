from __future__ import annotations

import json
import re
from typing import Any

from ollama import Client


class LocalLLM:
    def __init__(self, model: str, host: str):
        self.model = model
        self.client = Client(host=host)

    def chat_text(self, system_prompt: str, user_prompt: str) -> str:
        response = self.client.chat(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        return response.get("message", {}).get("content", "") or ""

    def chat_json(self, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        instruction = (
            user_prompt
            + "\n\nReturn only a valid JSON object. Do not include markdown fences."
        )
        raw = self.chat_text(system_prompt=system_prompt, user_prompt=instruction).strip()
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", raw, flags=re.DOTALL)
            if not match:
                return {}
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                return {}

