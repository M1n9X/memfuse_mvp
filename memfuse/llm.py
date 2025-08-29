from __future__ import annotations

from typing import List

from openai import OpenAI

from .config import Settings


class ChatLLM:
    def __init__(self, settings: Settings) -> None:
        # Only pass base_url if provided to allow library defaults
        if settings.openai_base_url:
            self.client = OpenAI(api_key=settings.openai_api_key, base_url=settings.openai_base_url)
        else:
            self.client = OpenAI(api_key=settings.openai_api_key)
        self.model = settings.openai_model
        self.system_prompt_text = settings.system_prompt
        self.assistant_role_target = getattr(settings, "openai_assistant_role", "assistant")

    def chat(self, system_prompt: str, messages: List[dict]) -> str:
        # messages: list of {role, content}
        # Some OpenAI-compatible backends (e.g., Google Gemini proxy) use role "model" instead of "assistant".
        # Normalize roles to backend expectations based on env setting.
        normalized: List[dict] = []
        assistant_role = self.system_prompt_text and "system" or "system"
        # prepend system prompt
        normalized.append({"role": "system", "content": system_prompt})
        for m in messages:
            role = m.get("role", "")
            content = m.get("content", "")
            if role in ("assistant", "ai"):
                # Map to target role per backend requirements (assistant or model)
                role = self.assistant_role_target
            elif role == "user":
                role = "user"
            elif role == "system":
                role = "system"
            else:
                # fall back to user if unknown
                role = "user"
            normalized.append({"role": role, "content": content})
        completion = self.client.chat.completions.create(
            model=self.model,
            messages=normalized,
        )
        return completion.choices[0].message.content or ""
