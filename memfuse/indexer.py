from __future__ import annotations

from typing import Iterable, List
from uuid import uuid4

from .embeddings import JinaEmbeddingClient
from .db import Database
from .utils import compute_content_hash


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
        # Deduplicate by hash to avoid re-inserting the same content
        deduped: list[tuple[str, str]] = []
        seen_hashes: set[str] = set()
        for content in contents:
            h = compute_content_hash(content)
            if h in seen_hashes:
                continue
            seen_hashes.add(h)
            deduped.append((content, h))
        if not deduped:
            return 0
        embs = self.embedder.embed([c for c, _h in deduped])
        added = 0
        for (content, h), emb in zip(deduped, embs):
            self.db.insert_document_chunk(str(uuid4()), f"session:{session_id}", content, emb, content_hash=h)
            added += 1
        return added
