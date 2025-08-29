from __future__ import annotations

from typing import Iterable

import tiktoken


def count_tokens(text: str, model: str | None = None) -> int:
    # Use cl100k_base as a generic tokenizer
    enc = tiktoken.get_encoding("cl100k_base")
    return len(enc.encode(text))


def truncate_by_tokens(text: str, max_tokens: int) -> str:
    enc = tiktoken.get_encoding("cl100k_base")
    ids = enc.encode(text)
    if len(ids) <= max_tokens:
        return text
    truncated_ids = ids[-max_tokens:]
    return enc.decode(truncated_ids)


def truncate_messages_by_tokens(messages: list[dict], max_tokens: int) -> list[dict]:
    # Roughly truncate by message order while respecting max_tokens.
    # Always try to keep at least the last message (truncated if needed).
    enc = tiktoken.get_encoding("cl100k_base")
    if max_tokens <= 0 or not messages:
        return []
    total = 0
    kept: list[dict] = []
    # Keep only the tail (most recent) messages
    for msg in reversed(messages):
        content = msg.get("content", "")
        tokens = len(enc.encode(content)) + 4
        if total + tokens > max_tokens:
            # If we haven't kept anything yet, include a truncated version of this message
            if not kept:
                budget = max_tokens - 4
                truncated = truncate_by_tokens(content, max(0, budget))
                if truncated:
                    kept.append({**msg, "content": truncated})
                    total = max_tokens
            break
        kept.append(msg)
        total += tokens
    kept.reverse()
    return kept
