from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import List

from .config import Settings
from .db import Database
from .embeddings import JinaEmbeddingClient
from .llm import ChatLLM
from .context import ContextController, RetrievedChunk


@dataclass
class RAGService:
    settings: Settings
    db: Database
    embedder: JinaEmbeddingClient
    llm: ChatLLM
    context: ContextController

    @classmethod
    def from_settings(cls, settings: Settings) -> "RAGService":
        return cls(
            settings=settings,
            db=Database.from_settings(settings),
            embedder=JinaEmbeddingClient(settings),
            llm=ChatLLM(settings),
            context=ContextController(settings),
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

    def chat(self, session_id: str, user_query: str) -> str:
        # Step 1: history truncation (load recent history; exact token truncation occurs in ContextController)
        history = self.db.fetch_conversation_history(session_id=session_id)

        # Step 2: retrieval
        query_embedding = self.embedder.embed([user_query])[0]
        rows = self.db.search_similar_chunks(query_embedding, self.settings.rag_top_k)
        retrieved = [RetrievedChunk(content=r[0], source=r[1], score=r[2]) for r in rows]

        # Step 3: context construction
        messages = self.context.build_final_context(user_query, history, retrieved)

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
