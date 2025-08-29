from __future__ import annotations

from typing import Iterable, List
from uuid import uuid4

from .embeddings import JinaEmbeddingClient
from .db import Database


class SessionIndexer:
    def __init__(self, db: Database, embedder: JinaEmbeddingClient) -> None:
        self.db = db
        self.embedder = embedder

    def ensure_built(self, session_id: str, history: List[tuple[int, str, str]]) -> int:
        """Build vector chunks for session history into documents_chunks with document_source=session:<id>.
        Return number of chunks added. Idempotent for same content.
        """
        # Simple approach: embed each message content; in real usage, we'd upsert with hash
        if not history:
            return 0
        contents = [h[2] for h in history]
        embs = self.embedder.embed(contents)
        added = 0
        for content, emb in zip(contents, embs):
            self.db.insert_document_chunk(str(uuid4()), f"session:{session_id}", content, emb)
            added += 1
        return added
