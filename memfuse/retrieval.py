from __future__ import annotations

from dataclasses import dataclass
from typing import List

from .config import Settings
from .db import Database
from .embeddings import JinaEmbeddingClient
from .context import RetrievedChunk


__all__ = ["BasicRetrievalStrategy"]


@dataclass
class BasicRetrievalStrategy:
    """Default retrieval that prefers session-scoped chunks, with safe fallbacks.

    Order of attempts:
    1) Embed query and do pgvector similarity search over session chunks if present
       else over global chunks
    2) Fallback to Top-K (no similarity) for session/global
    3) If still empty and we have history, use recent history lines as pseudo-chunks
    """

    db: Database
    embedder: JinaEmbeddingClient
    settings: Settings

    def _extract_keywords(self, text: str, max_terms: int = 8) -> List[str]:
        # naive multilingual keyword extraction: capture alphanumerics and CJK sequences
        import re
        latin = re.findall(r"[A-Za-z0-9_\-]+", text)
        cjk = re.findall(r"[\u4e00-\u9fff]{2,}", text)
        tokens = latin + cjk
        seen: list[str] = []
        for t in tokens:
            tl = t.lower()
            if len(tl) <= 1:
                continue
            if tl not in seen:
                seen.append(tl)
            if len(seen) >= max_terms:
                break
        return seen

    def retrieve(
        self,
        session_id: str,
        user_query: str,
        history: List[tuple[int, str, str]],
    ) -> List[RetrievedChunk]:
        rows: list[tuple[str, str, float]] = []
        structured_rows: list[tuple[str, str, float]] = []

        # Compute query embedding once and reuse across structured + unstructured retrieval
        query_embedding: List[float] | None = None
        try:
            query_embedding = self.embedder.embed([user_query])[0]
        except Exception:
            query_embedding = None

        # 2.1 Structured retrieval (exact-ish) if enabled
        if getattr(self.settings, "structured_enabled", False):
            try:
                k_struct = getattr(self.settings, "structured_top_k", 0) or (self.settings.rag_top_k * 2)
                if query_embedding is not None:
                    structured_rows = self.db.query_structured_similar(session_id, query_embedding, k_struct)
                # If vector returns empty (e.g., no embeddings yet), fallback to keyword query
                if not structured_rows:
                    keywords = self._extract_keywords(user_query)
                    structured_rows = self.db.query_structured_by_keywords(session_id, keywords, k_struct)
            except Exception:
                structured_rows = []

        prefer_session = self.settings.retrieval_prefer_session
        has_session_chunks = False
        if prefer_session:
            try:
                has_session_chunks = self.db.count_session_chunks(session_id) > 0
            except Exception:
                has_session_chunks = False

        if query_embedding is not None:
            try:
                if prefer_session and has_session_chunks:
                    rows = self.db.search_similar_chunks_for_session(
                        query_embedding, self.settings.rag_top_k, session_id
                    )
                else:
                    rows = self.db.search_similar_chunks(query_embedding, self.settings.rag_top_k)
            except Exception:
                rows = []

        # Merge structured and vector results if any
        merged: list[tuple[str, str, float]] = []
        # dedupe by content+source
        seen_keys: set[tuple[str, str]] = set()
        for lst in (structured_rows, rows):
            for c, s, sc in lst:
                key = (c, s)
                if key in seen_keys:
                    continue
                seen_keys.add(key)
                merged.append((c, s, sc))

        if not merged:
            # Fallback: basic strategy - return top K chunks without similarity
            try:
                if prefer_session and has_session_chunks:
                    merged = self.db.fetch_top_k_chunks_for_session(
                        min(3, self.settings.rag_top_k), session_id
                    )
                else:
                    merged = self.db.fetch_top_k_chunks(min(3, self.settings.rag_top_k))
            except Exception:
                merged = []

        if not merged and history:
            # Fallback 2: derive chunks from recent history if no documents available
            recent = history[-3:]
            merged = [(h[2], f"history#{h[0]}:{h[1]}", 0.0) for h in recent]

        return [RetrievedChunk(content=r[0], source=r[1], score=r[2]) for r in merged]
