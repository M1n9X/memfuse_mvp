from __future__ import annotations

import json
from dataclasses import dataclass
from typing import List, Tuple
from uuid import uuid4

from .config import Settings
from .db import Database
from .llm import ChatLLM
from .embeddings import JinaEmbeddingClient
from .retrieval import BasicRetrievalStrategy


EXTRACTOR_SYSTEM_PROMPT = (
    "You are a precise information extractor. Given one conversation round (user + ai) and optional related context, "
    "extract high-quality structured items as strict JSON. Do not include explanations.\n\n"
    "Principles:\n"
    "- Each item MUST be standalone and self-explanatory. Expand or define acronyms and references so the fact can be used alone.\n"
    "- Prefer concise, high-information sentences (MECE: mutually exclusive, collectively exhaustive).\n"
    "- Merge micro-facts about the same subject into one compact statement. Avoid repeating the same subject across multiple facts.\n"
    "- If the round contains only a short user question, you may still extract a fact or decision if the AI response provides sufficient context.\n"
    "- Only include items that are grounded by the given round and related context.\n\n"
    "Schema (JSON):\n"
    "{\n"
    "  \"items\": [\n"
    "    {\n"
    "      \"type\": \"Fact|Decision|Assumption|User_Preference\",\n"
    "      \"content\": \"<self-contained, concise statement with expanded terms>\",\n"
    "      \"relations\": {\"based_on\": [\"<fact_id_ref>\"], \"contradicts\": \"<fact_id_ref>\"},\n"
    "      \"metadata\": {\"confidence\": <0..1>}\n"
    "    }\n"
    "  ]\n"
    "}\n"
)


def _build_user_prompt(round_messages: List[Tuple[int, str, str]],
                       related_structured: List[Tuple[str, str, float]] | None = None,
                       related_chunks: List[Tuple[str, str, float]] | None = None) -> str:
    # round_messages: list of (round_id, speaker, content)
    # Detect language from AI content and/or user content to guide output language
    def detect_lang(s: str) -> str:
        import re
        if re.search(r"[\u4e00-\u9fff]", s):
            return "zh"
        return "en"

    ai_text = next((c for _rid, spk, c in round_messages if spk == "ai"), "")
    user_text = next((c for _rid, spk, c in round_messages if spk == "user"), "")
    lang = detect_lang(ai_text or user_text)

    lines: List[str] = [
        "Extract structured items from this conversation round.",
        "Write items in the same language as the AI response.",
        "If the new information is redundant with the provided related facts, you may return an empty items list.",
        "If a contradiction exists, favor the most recent information and indicate it in relations.contradicts when possible.",
    ]
    for rid, speaker, content in round_messages:
        role = "User" if speaker == "user" else "AI"
        lines.append(f"[{role} #{rid}] {content}")
    # Add related structured memory for better recall context
    if related_structured:
        lines.append("\n[Related Structured Memory]")
        for content, src, _score in related_structured[:8]:
            lines.append(f"- {src}: {content}")
    # Add related unstructured chunks
    if related_chunks:
        lines.append("\n[Related Chunks]")
        for content, src, _score in related_chunks[:8]:
            lines.append(f"- {src}: {content}")
    return "\n".join(lines)


@dataclass
class MemoryExtractor:
    settings: Settings
    db: Database
    llm: ChatLLM
    embedder: JinaEmbeddingClient

    def extract_and_store(
        self, session_id: str, round_id: int, round_messages: List[Tuple[int, str, str]]
    ) -> int:
        # Build prompts (simple mode, without expansions)
        user_prompt = _build_user_prompt(round_messages)
        # Request JSON response
        raw = self.llm.completion_json(EXTRACTOR_SYSTEM_PROMPT, user_prompt)
        try:
            data = json.loads(raw or "{}")
        except Exception:
            return 0
        items = data.get("items")
        if not isinstance(items, list):
            return 0

        records: List[Tuple[str, str, int, str, str, dict, dict, List[float] | None]] = []
        for item in items[:16]:  # cap to avoid flooding
            try:
                typ = str(item.get("type", "Fact"))
                content = str(item.get("content", "")).strip()
                if not content:
                    continue
                relations = item.get("relations") or {}
                metadata = item.get("metadata") or {}
                # embed content for dedup/semantic recall later
                emb: List[float] | None = None
                try:
                    emb = self.embedder.embed([content])[0]
                except Exception:
                    emb = None
                records.append(
                    (
                        str(uuid4()),
                        session_id,
                        int(round_id),
                        typ,
                        content,
                        relations,
                        metadata,
                        emb,
                    )
                )
            except Exception:
                continue

        if not records:
            return 0
        try:
            inserted = self.db.insert_structured_records(records)
        except Exception:
            inserted = 0
        # Mark rounds extracted only if we actually inserted items
        if inserted > 0:
            try:
                self.db.mark_rounds_extracted(session_id, [round_id])
            except Exception:
                pass
        return inserted

    def extract_if_needed_batch(self, session_id: str, pending_rounds: List[Tuple[int, str, str]], trigger_tokens: int) -> int:
        """Given a list of unextracted rounds (rid, user, ai), decide if we should extract now.

        - If the last round alone exceeds trigger_tokens, extract it immediately.
        - Otherwise, accumulate from oldest until reaching/exceeding trigger_tokens, then extract together.
        Returns number of inserted structured records (approx).
        """
        if not pending_rounds:
            return 0
        from .tokenizer import count_tokens
        # Evaluate last round size
        last_rid, last_user, last_ai = pending_rounds[-1]
        last_tokens = count_tokens(last_user) + count_tokens(last_ai)
        rounds_to_extract: List[Tuple[int, str, str]] = []
        if last_tokens >= trigger_tokens:
            rounds_to_extract = [(last_rid, last_user, last_ai)]
        else:
            # Accumulate from oldest
            total = 0
            for rid, u, a in pending_rounds:
                total += count_tokens(u) + count_tokens(a)
                rounds_to_extract.append((rid, u, a))
                if total >= trigger_tokens:
                    break
            # If still under threshold, skip extraction for now
            if total < trigger_tokens:
                return 0

        # Build a combined prompt over selected rounds + related context
        # Flatten messages per round into the (rid, speaker, content) triplets expected by _build_user_prompt
        flattened: List[Tuple[int, str, str]] = []
        for rid, u, a in rounds_to_extract:
            if u:
                flattened.append((rid, "user", u))
            if a:
                flattened.append((rid, "ai", a))
        # Use the last rid as the marking target if multiple rounds
        mark_ids = [rid for rid, _u, _a in rounds_to_extract]
        # Related context retrieval
        related_structured: List[Tuple[str, str, float]] = []
        related_chunks: List[Tuple[str, str, float]] = []
        try:
            # Use keywords from the most recent round's text for searching
            last_text = (last_user + "\n" + last_ai).strip()
            # Prefer structured
            keywords = BasicRetrievalStrategy(self.db, None, self.settings)._extract_keywords(last_text)  # type: ignore
            if keywords:
                related_structured = self.db.query_structured_by_keywords(
                    session_id, keywords, getattr(self.settings, "structured_top_k", 5) * 2
                )
        except Exception:
            related_structured = []
        try:
            # Vector-based related chunk retrieval
            vec = self.embedder.embed([last_text])[0]
            prefer_session = getattr(self.settings, "retrieval_prefer_session", True)
            has_session_chunks = False
            if prefer_session:
                try:
                    has_session_chunks = self.db.count_session_chunks(session_id) > 0
                except Exception:
                    has_session_chunks = False
            if prefer_session and has_session_chunks:
                related_chunks = self.db.search_similar_chunks_for_session(vec, 5, session_id)
            else:
                related_chunks = self.db.search_similar_chunks(vec, 5)
        except Exception:
            # Fallback to simple top-k without similarity
            try:
                related_chunks = self.db.fetch_top_k_chunks_for_session(5, session_id)
            except Exception:
                related_chunks = []
            if not related_chunks:
                try:
                    related_chunks = self.db.fetch_top_k_chunks(5)
                except Exception:
                    related_chunks = []

        # MECE-aware skip check: fetch top-K similar structured facts for dedup/contradiction reasoning
        similar_structured: List[Tuple[str, str, float]] = []
        try:
            vec = self.embedder.embed([last_text])[0]
            similar_structured = self.db.query_structured_similar(
                session_id, vec, getattr(self.settings, "extractor_dedup_top_k", 10)
            )
        except Exception:
            similar_structured = []

        # Build prompt including related facts/chunks and the top-k similar facts for MECE/contradiction handling
        # We append similar_structured to related_structured to keep a single section; dedupe by content
        seen_facts = set(c for c, _s, _sc in related_structured)
        for c, s, sc in similar_structured:
            if c not in seen_facts:
                related_structured.append((c, s, sc))
                seen_facts.add(c)

        user_prompt = _build_user_prompt(flattened, related_structured, related_chunks)
        raw = self.llm.completion_json(EXTRACTOR_SYSTEM_PROMPT, user_prompt)
        try:
            data = json.loads(raw or "{}")
        except Exception:
            return 0
        items = data.get("items")
        if not isinstance(items, list):
            return 0
        records: List[Tuple[str, str, int, str, str, dict, dict, List[float] | None]] = []
        for item in items[:24]:
            try:
                typ = str(item.get("type", "Fact"))
                content = str(item.get("content", "")).strip()
                if not content:
                    continue
                relations = item.get("relations") or {}
                metadata = item.get("metadata") or {}
                # Use last round id as source_round_id to represent the batch
                emb: List[float] | None = None
                try:
                    emb = self.embedder.embed([content])[0]
                except Exception:
                    emb = None
                records.append((str(uuid4()), session_id, int(mark_ids[-1]), typ, content, relations, metadata, emb))
            except Exception:
                continue
        if not records:
            return 0
        inserted = 0
        try:
            inserted = self.db.insert_structured_records(records)
        except Exception:
            inserted = 0
        # Mark all included rounds as extracted only if we actually inserted items
        if inserted > 0:
            try:
                self.db.mark_rounds_extracted(session_id, mark_ids)
            except Exception:
                pass
        return inserted
