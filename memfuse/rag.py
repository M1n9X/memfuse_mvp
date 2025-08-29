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
from .retrieval import BasicRetrievalStrategy
from .utils import compute_content_hash
from .structured import MemoryExtractor


@dataclass
class RAGService:
    """High-level orchestrator for Phase-1 Pgvector-based RAG pipeline.

    Responsibilities:
    - Ingestion: chunk input text, embed, and persist to `documents_chunks`.
    - Chat: load history, ensure session index, retrieve similar chunks, build context,
      call LLM, and persist the new turn into `conversations`.
    """
    settings: Settings
    db: Database
    embedder: JinaEmbeddingClient
    llm: ChatLLM
    context: ContextController
    indexer: SessionIndexer
    retrieval: BasicRetrievalStrategy | None = None
    extractor: MemoryExtractor | None = None

    @classmethod
    def from_settings(cls, settings: Settings) -> "RAGService":
        service = cls(
            settings=settings,
            db=Database.from_settings(settings),
            embedder=JinaEmbeddingClient(settings),
            llm=ChatLLM(settings),
            context=ContextController(settings),
            indexer=SessionIndexer(Database.from_settings(settings), JinaEmbeddingClient(settings)),
        )
        # Initialize default retrieval strategy (pluggable)
        service.retrieval = BasicRetrievalStrategy(service.db, service.embedder, service.settings)
        # Initialize extractor for Phase 2
        try:
            service.extractor = MemoryExtractor(service.settings, service.db, service.llm, JinaEmbeddingClient(settings))
        except Exception:
            service.extractor = None
        return service

    def ingest_document(self, document_source: str, content: str, chunk_size: int = 800) -> int:
        chunks = self._chunk_text(content, chunk_size)
        # Compute hashes first and drop duplicates within this batch
        seen_hashes: set[str] = set()
        deduped: list[tuple[str, str]] = []  # (text, hash)
        for text in chunks:
            h = compute_content_hash(text)
            if h in seen_hashes:
                continue
            seen_hashes.add(h)
            deduped.append((text, h))
        if not deduped:
            return 0
        embeddings = self.embedder.embed([t for (t, _h) in deduped])
        inserted = 0
        for (text, h), emb in zip(deduped, embeddings):
            # Rely on DB-side ON CONFLICT to avoid duplicates across runs
            self.db.insert_document_chunk(
                chunk_id=str(uuid.uuid4()),
                document_source=document_source,
                content=text,
                embedding=emb,
                content_hash=h,
            )
            inserted += 1
        return inserted

    def chat(self, session_id: str, user_query: str, trace: ContextTrace | None = None) -> str:
        # Step 1: history truncation (load recent history; exact token truncation occurs in ContextController)
        # For efficiency, fetch only a bounded number of recent rounds from DB; fine truncation happens in ContextController
        try:
            history = self.db.fetch_conversation_history(session_id=session_id, limit_rounds=self.settings.history_fetch_rounds)
        except Exception:
            history = []

        # Step 2: retrieval (ensure session index exists/updated)
        try:
            self.indexer.ensure_built(session_id, history)
        except Exception:
            pass
        # Now perform retrieval via strategy
        if self.retrieval is None:
            self.retrieval = BasicRetrievalStrategy(self.db, self.embedder, self.settings)
        retrieved = self.retrieval.retrieve(session_id, user_query, history)

        # Step 3: context construction
        messages = self.context.build_final_context(user_query, history, retrieved, trace=trace)

        # Step 4: LLM call
        answer = self.llm.chat(system_prompt=self.settings.system_prompt, messages=messages)

        # Step 5: store memory
        round_id = (history[-1][0] + 1) if history else 1
        try:
            self.db.insert_conversation_message(session_id, round_id, "user", user_query)
            self.db.insert_conversation_message(session_id, round_id, "ai", answer)
        except Exception:
            pass

        # Phase 2: trigger extractor with token-aware batching policy
        if getattr(self.settings, "extractor_enabled", False) and self.extractor is not None and getattr(self.settings, "structured_enabled", False):
            try:
                # Fetch unextracted rounds and decide whether to extract now
                pending = self.db.fetch_unextracted_rounds(session_id)
                # If DB unavailable, fallback to just current round best-effort
                if not pending:
                    self.extractor.extract_and_store(session_id, round_id, [
                        (round_id, "user", user_query),
                        (round_id, "ai", answer),
                    ])
                else:
                    # Ensure current round included (in case of race)
                    if not any(rid == round_id for rid, _u, _a in pending):
                        pending.append((round_id, user_query, answer))
                    self.extractor.extract_if_needed_batch(
                        session_id, pending, self.settings.extractor_trigger_tokens
                    )
            except Exception:
                pass
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
