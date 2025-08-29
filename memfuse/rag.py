from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import List

from .config import Settings
from .db import Database
from .embeddings import JinaEmbeddingClient
from .llm import ChatLLM
from .context import ContextController, RetrievedChunk
from .tracing import ContextTrace
from .indexer import SessionIndexer


@dataclass
class RAGService:
    settings: Settings
    db: Database
    embedder: JinaEmbeddingClient
    llm: ChatLLM
    context: ContextController
    indexer: SessionIndexer

    @classmethod
    def from_settings(cls, settings: Settings) -> "RAGService":
        return cls(
            settings=settings,
            db=Database.from_settings(settings),
            embedder=JinaEmbeddingClient(settings),
            llm=ChatLLM(settings),
            context=ContextController(settings),
            indexer=SessionIndexer(Database.from_settings(settings), JinaEmbeddingClient(settings)),
        )

    def ingest_document(self, document_source: str, content: str, chunk_size: int = 800) -> int:
        chunks = self._chunk_text(content, chunk_size)
        embeddings = self.embedder.embed(chunks)
        for text, emb in zip(chunks, embeddings):
            self.db.insert_document_chunk(
                chunk_id=str(uuid.uuid4()),
                document_source=document_source,
                content=text,
                embedding=emb,
            )
        return len(chunks)

    def chat(self, session_id: str, user_query: str, trace: ContextTrace | None = None) -> str:
        # Step 1: history truncation (load recent history; exact token truncation occurs in ContextController)
        history = self.db.fetch_conversation_history(session_id=session_id)

        # Step 2: retrieval (ensure session index exists/updated)
        try:
            self.indexer.ensure_built(session_id, history)
        except Exception:
            pass
        # Now perform retrieval
        rows: list[tuple[str, str, float]] = []
        try:
            query_embedding = self.embedder.embed([user_query])[0]
            # Prefer session-scoped chunks if available; else global
            if self.db.count_session_chunks(session_id) > 0:
                rows = self.db.search_similar_chunks_for_session(query_embedding, self.settings.rag_top_k, session_id)
            else:
                rows = self.db.search_similar_chunks(query_embedding, self.settings.rag_top_k)
        except Exception:
            rows = []
        if not rows:
            # Fallback: basic strategy - return top K chunks without similarity
            if self.db.count_session_chunks(session_id) > 0:
                rows = self.db.fetch_top_k_chunks_for_session(min(3, self.settings.rag_top_k), session_id)
            else:
                rows = self.db.fetch_top_k_chunks(min(3, self.settings.rag_top_k))
        if not rows and history:
            # Fallback 2: derive chunks from recent history if no documents available
            recent = history[-3:]
            rows = [(h[2], f"history#{h[0]}:{h[1]}", 0.0) for h in recent]
        retrieved = [RetrievedChunk(content=r[0], source=r[1], score=r[2]) for r in rows]

        # Step 3: context construction
        messages = self.context.build_final_context(user_query, history, retrieved, trace=trace)

        # Step 4: LLM call
        answer = self.llm.chat(system_prompt=self.settings.system_prompt, messages=messages)

        # Step 5: store memory
        round_id = (history[-1][0] + 1) if history else 1
        self.db.insert_conversation_message(session_id, round_id, "user", user_query)
        self.db.insert_conversation_message(session_id, round_id, "ai", answer)
        return answer

    def _chunk_text(self, text: str, chunk_size: int) -> List[str]:
        paragraphs: list[str] = []
        current = []
        words = text.split()
        for word in words:
            current.append(word)
            if len(current) >= chunk_size:
                paragraphs.append(" ".join(current))
                current = []
        if current:
            paragraphs.append(" ".join(current))
        return paragraphs
