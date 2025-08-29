from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Tuple

# Avoid circular imports: repeat lightweight types if needed


@dataclass
class ContextTrace:
    # User input
    user_tokens_before: int = 0
    user_tokens_after: int = 0
    user_truncated: bool = False

    # History
    history_tokens_before: int = 0
    history_tokens_after: int = 0
    history_truncated: bool = False
    history_rounds_before: int = 0
    history_rounds_after: int = 0
    dropped_messages: List[Tuple[int, str, str]] = field(default_factory=list)  # (round_id, speaker, content)
    history_kept_messages: List[Tuple[str, str]] = field(default_factory=list)  # (role, content)

    # Summary
    summary_added: bool = False
    summary_tokens: int = 0
    summary_text: str = ""

    # Retrieval
    retrieved_top_k: int = 0
    retrieved_count: int = 0
    retrieved_preview: List[Tuple[str, float]] = field(default_factory=list)  # (source, score)
    retrieved_block_content: str = ""

    # Final context
    final_messages_count: int = 0
    final_tokens_estimate: int = 0
    final_messages: List[dict] = field(default_factory=list)
    system_prompt_text: str = ""
