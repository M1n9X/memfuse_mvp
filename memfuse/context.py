from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple

from .config import Settings
from .tokenizer import count_tokens, truncate_by_tokens, truncate_messages_by_tokens


@dataclass
class RetrievedChunk:
    content: str
    source: str
    score: float


class ContextController:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def build_final_context(
        self,
        user_query: str,
        conversation_history: List[Tuple[int, str, str]],  # (round_id, speaker, content)
        retrieved_chunks: List[RetrievedChunk],
    ) -> list[dict]:
        # Enforce user input limit
        user_query_text = truncate_by_tokens(user_query, self.settings.user_input_max_tokens)

        # Prepare conversation messages
        history_messages: list[dict] = [
            {"role": speaker, "content": content}
            for _, speaker, content in conversation_history
        ]
        history_messages = truncate_messages_by_tokens(
            history_messages, self.settings.history_max_tokens
        )

        # Inject retrieved chunks as a system-style context block
        chunks_text = "\n\n".join(
            [f"[Source: {c.source} | Score: {c.score:.3f}]\n{c.content}" for c in retrieved_chunks]
        )
        retrieved_block = {
            "role": "system",
            "content": f"Relevant knowledge:\n{chunks_text}" if chunks_text else "",
        }

        # Per PRD: final_context = user_query + retrieved_chunks + conversation_history + system_prompt
        # We'll structure messages accordingly before passing to LLM wrapper (which prepends system prompt).
        candidate = [
            {"role": "user", "content": user_query_text},
            retrieved_block,
        ] + history_messages

        # Trim to total context limit
        while self._messages_token_count(candidate) > self.settings.total_context_max_tokens:
            # Drop oldest history first
            if history_messages:
                history_messages.pop(0)
                candidate = [
                    {"role": "user", "content": user_query_text},
                    retrieved_block,
                ] + history_messages
            else:
                # As a last resort, truncate retrieved_block and user content further
                retrieved_block["content"] = truncate_by_tokens(
                    retrieved_block.get("content", ""),
                    max(0, self.settings.total_context_max_tokens // 2),
                )
                user_query_text = truncate_by_tokens(
                    user_query_text, max(0, self.settings.total_context_max_tokens // 4)
                )
                candidate = [
                    {"role": "user", "content": user_query_text},
                    retrieved_block,
                ]
                break

        return candidate

    def _messages_token_count(self, messages: list[dict]) -> int:
        return sum(count_tokens(m.get("content", "")) + 4 for m in messages)
