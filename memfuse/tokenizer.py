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
    # Roughly truncate by message order while respecting max_tokens
    enc = tiktoken.get_encoding("cl100k_base")
    total = 0
    kept: list[dict] = []
    # Keep only the tail (most recent) messages
    for msg in reversed(messages):
        tokens = len(enc.encode(msg.get("content", ""))) + 4
        if total + tokens > max_tokens:
            break
        kept.append(msg)
        total += tokens
    kept.reverse()
    return kept
