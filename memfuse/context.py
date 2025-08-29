from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple, Optional

from .config import Settings
from .tokenizer import count_tokens, truncate_by_tokens, truncate_messages_by_tokens
from .tracing import ContextTrace


@dataclass
class RetrievedChunk:
    content: str
    source: str
    score: float


class ContextController:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def _summarize_dropped_messages(self, dropped: List[Tuple[int, str, str]], max_tokens: int = 256) -> str:
        # Naive summary: take first sentence or up to 30 words from each dropped message
        # and join as bullet points. Then enforce token cap.
        bullets: list[str] = []
        for (_rid, speaker, content) in dropped:
            text = content.strip().split('\n', 1)[0]
            # split by typical sentence enders
            for sep in ['。', '！', '？', '.', '!', '?']:
                if sep in text:
                    text = text.split(sep)[0] + sep
                    break
            words = text.split()
            if len(words) > 30:
                text = ' '.join(words[:30]) + '...'
            label = 'User' if speaker == 'user' else 'AI'
            bullets.append(f"- {label}: {text}")
        combined = "History summary (compressed):\n" + "\n".join(bullets[:10])
        return truncate_by_tokens(combined, max_tokens)

    def build_final_context(
        self,
        user_query: str,
        conversation_history: List[Tuple[int, str, str]],  # (round_id, speaker, content)
        retrieved_chunks: List[RetrievedChunk],
        trace: Optional[ContextTrace] = None,
    ) -> list[dict]:
        # Enforce user input limit
        user_tokens_before = count_tokens(user_query)
        user_query_text = truncate_by_tokens(user_query, self.settings.user_input_max_tokens)
        if trace is not None:
            trace.user_tokens_before = user_tokens_before
            trace.user_tokens_after = count_tokens(user_query_text)
            trace.user_truncated = trace.user_tokens_after < trace.user_tokens_before

        # Prepare conversation messages
        history_messages: list[dict] = [
            {"role": speaker, "content": content}
            for _, speaker, content in conversation_history
        ]
        if trace is not None:
            trace.history_rounds_before = len(conversation_history)
            trace.history_tokens_before = sum(count_tokens(m[2]) + 4 for m in conversation_history)
        truncated_history = truncate_messages_by_tokens(history_messages, self.settings.history_max_tokens)
        if trace is not None:
            trace.history_rounds_after = len(truncated_history)
            trace.history_tokens_after = sum(count_tokens(m.get("content","")) + 4 for m in truncated_history)
            trace.history_truncated = trace.history_tokens_after < trace.history_tokens_before
            if trace.history_truncated:
                # roughly compute dropped messages by comparing tail kept
                kept_set = set((m.get("role",""), m.get("content","")) for m in truncated_history)
                for (rid, spk, cont) in conversation_history:
                    if (spk, cont) not in kept_set:
                        trace.dropped_messages.append((rid, spk, cont))
            trace.history_kept_messages = [(m.get("role",""), m.get("content","")) for m in truncated_history]
        history_messages = truncated_history

        # Inject retrieved chunks as a system-style context block with explicit section headers
        # Split into facts vs chunks and present in separate sections
        structured = [c for c in retrieved_chunks if str(c.source).startswith("structured:")]
        unstructured = [c for c in retrieved_chunks if not str(c.source).startswith("structured:")]
        facts_text = "\n\n".join(
            [f"- Fact: {c.content}\n  Source: {c.source} (score={c.score:.3f})" for c in structured]
        )
        chunks_text = "\n\n".join(
            [f"- Source: {c.source} (score={c.score:.3f})\n{c.content}" for c in unstructured]
        )
        content_blocks = []
        if facts_text:
            content_blocks.append("[Retrieved Facts]\n" + facts_text)
        if chunks_text:
            content_blocks.append("[Retrieved Chunks]\n" + chunks_text)
        retrieved_block = {
            "role": "system",
            "content": "\n\n".join(content_blocks),
        }
        if trace is not None:
            trace.retrieved_top_k = len(retrieved_chunks)
            trace.retrieved_count = len(retrieved_chunks)
            trace.retrieved_preview = [(c.source, c.score) for c in retrieved_chunks[:5]]
            trace.retrieved_block_content = retrieved_block["content"]
            trace.retrieved_facts_count = len(structured)
            trace.retrieved_chunks_count = len(unstructured)
            trace.retrieved_facts_preview = [(c.source, c.score) for c in structured[:5]]
            trace.retrieved_chunks_preview = [(c.source, c.score) for c in unstructured[:5]]

        # Build blocks: system(retrieved), optional system(summary), history, user
        prefix_blocks: list[dict] = []
        if retrieved_block.get("content"):
            prefix_blocks.append(retrieved_block)

        # If history was truncated, add a compressed summary of dropped content
        summary_block: dict | None = None
        if trace is not None and trace.history_truncated and trace.dropped_messages:
            summary_text = self._summarize_dropped_messages(trace.dropped_messages)
            if summary_text:
                summary_block = {"role": "system", "content": summary_text}
                trace.summary_added = True
                trace.summary_text = summary_text
                trace.summary_tokens = count_tokens(summary_text)
                prefix_blocks.append(summary_block)

        candidate = prefix_blocks + history_messages + [
            {"role": "user", "content": user_query_text}
        ]

        # Trim to total context limit
        while self._messages_token_count(candidate) > self.settings.total_context_max_tokens:
            # Drop oldest history first
            if history_messages:
                history_messages.pop(0)
                candidate = prefix_blocks + history_messages + [
                    {"role": "user", "content": user_query_text}
                ]
            else:
                # As a last resort, truncate retrieved_block and user content further
                # Keep a small retrieved header + first chunk preview instead of dropping entirely
                rb = retrieved_block.get("content", "")
                header = "[Retrieved Chunks]\n"
                body = rb[len(header):] if rb.startswith(header) else rb
                safe_rb = header + truncate_by_tokens(body, max(128, self.settings.total_context_max_tokens // 8))
                retrieved_block["content"] = safe_rb
                user_query_text = truncate_by_tokens(
                    user_query_text, max(64, self.settings.total_context_max_tokens // 6)
                )
                # Update prefix_blocks with possibly truncated retrieved content
                if prefix_blocks:
                    prefix_blocks[0] = retrieved_block
                candidate = prefix_blocks + [
                    {"role": "user", "content": user_query_text}
                ]
                break

        if trace is not None:
            trace.final_messages_count = len(candidate)
            trace.final_tokens_estimate = self._messages_token_count(candidate)
            trace.final_messages = candidate.copy()

        return candidate

    def _messages_token_count(self, messages: list[dict]) -> int:
        return sum(count_tokens(m.get("content", "")) + 4 for m in messages)
