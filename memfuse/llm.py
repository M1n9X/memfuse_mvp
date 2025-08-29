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

    def chat(self, system_prompt: str, messages: List[dict]) -> str:
        # messages: list of {role, content}
        all_messages = [{"role": "system", "content": system_prompt}] + messages
        completion = self.client.chat.completions.create(
            model=self.model,
            messages=all_messages,
        )
        return completion.choices[0].message.content or ""
