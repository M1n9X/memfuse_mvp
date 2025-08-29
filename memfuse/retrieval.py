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

    def retrieve(
        self,
        session_id: str,
        user_query: str,
        history: List[tuple[int, str, str]],
    ) -> List[RetrievedChunk]:
        rows: list[tuple[str, str, float]] = []
        try:
            query_embedding = self.embedder.embed([user_query])[0]
            prefer_session = self.settings.retrieval_prefer_session
            if prefer_session and self.db.count_session_chunks(session_id) > 0:
                rows = self.db.search_similar_chunks_for_session(
                    query_embedding, self.settings.rag_top_k, session_id
                )
            else:
                rows = self.db.search_similar_chunks(query_embedding, self.settings.rag_top_k)
        except Exception:
            rows = []

        if not rows:
            # Fallback: basic strategy - return top K chunks without similarity
            if self.db.count_session_chunks(session_id) > 0:
                rows = self.db.fetch_top_k_chunks_for_session(
                    min(3, self.settings.rag_top_k), session_id
                )
            else:
                rows = self.db.fetch_top_k_chunks(min(3, self.settings.rag_top_k))

        if not rows and history:
            # Fallback 2: derive chunks from recent history if no documents available
            recent = history[-3:]
            rows = [(h[2], f"history#{h[0]}:{h[1]}", 0.0) for h in recent]

        return [RetrievedChunk(content=r[0], source=r[1], score=r[2]) for r in rows]
