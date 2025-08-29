from __future__ import annotations

import contextlib
from dataclasses import dataclass
from typing import Iterator, Optional

import psycopg
from pgvector.psycopg import register_vector
from pgvector.utils import Vector

from .config import Settings


@dataclass
class Database:
    dsn: str

    @classmethod
    def from_settings(cls, settings: Settings) -> "Database":
        return cls(dsn=settings.database_url)

    @contextlib.contextmanager
    def connect(self) -> Iterator[psycopg.Connection]:
        conn = psycopg.connect(self.dsn, autocommit=True)
        try:
            register_vector(conn)
            yield conn
        finally:
            conn.close()

    def fetch_conversation_history(
        self, session_id: str, limit_rounds: Optional[int] = None
    ) -> list[tuple[int, str, str]]:
        """Return list of (round_id, speaker, content) ascending by round_id then timestamp.
        If limit_rounds is provided, return only the latest N rounds (both user and ai within them).
        """
        base = (
            "SELECT round_id, speaker, content FROM conversations WHERE session_id = %s"
        )
        order = " ORDER BY round_id ASC, timestamp ASC"
        params: list[object] = [session_id]
        if limit_rounds is None:
            query = base + order
        else:
            # Get latest N round_ids first, then fetch within that set
            query = (
                "WITH latest AS (SELECT DISTINCT round_id FROM conversations WHERE session_id = %s "
                "ORDER BY round_id DESC LIMIT %s) "
                "SELECT c.round_id, c.speaker, c.content FROM conversations c "
                "JOIN latest l ON l.round_id = c.round_id WHERE c.session_id = %s" + order
            )
            params = [session_id, limit_rounds, session_id]
        with self.connect() as conn:
            with conn.cursor() as cur:
                cur.execute(query, tuple(params))
                rows = cur.fetchall()
                return [(int(r[0]), str(r[1]), str(r[2])) for r in rows]

    def insert_conversation_message(
        self, session_id: str, round_id: int, speaker: str, content: str
    ) -> None:
        with self.connect() as conn, conn.cursor() as cur:
            cur.execute(
                "INSERT INTO conversations (session_id, round_id, speaker, content) "
                "VALUES (%s, %s, %s, %s) "
                "ON CONFLICT (session_id, round_id, speaker) DO UPDATE SET content = EXCLUDED.content",
                (session_id, round_id, speaker, content),
            )

    def insert_document_chunk(
        self, chunk_id: str, document_source: str, content: str, embedding: list[float]
    ) -> None:
        with self.connect() as conn, conn.cursor() as cur:
            cur.execute(
                "INSERT INTO documents_chunks (chunk_id, document_source, content, embedding) "
                "VALUES (%s, %s, %s, %s)",
                (chunk_id, document_source, content, embedding),
            )

    def search_similar_chunks(
        self, query_embedding: list[float], top_k: int
    ) -> list[tuple[str, str, float]]:
        """Return list of (content, document_source, distance) ordered by similarity."""
        sql = (
            "WITH q AS (SELECT %s::vector AS v) "
            "SELECT content, document_source, 1 - (embedding <=> q.v) AS cosine_similarity "
            "FROM documents_chunks, q ORDER BY embedding <=> q.v ASC LIMIT %s"
        )
        with self.connect() as conn, conn.cursor() as cur:
            vec = Vector(query_embedding)
            # Force sequential scan to avoid any ivfflat edge-case returning empty rows
            try:
                cur.execute("SET enable_indexscan = off; SET enable_bitmapscan = off;")
            except Exception:
                pass
            cur.execute(sql, (vec, top_k))
            rows = cur.fetchall()
            return [(str(r[0]), str(r[1]) if r[1] is not None else "", float(r[2])) for r in rows]

    def fetch_top_k_chunks(self, top_k: int) -> list[tuple[str, str, float]]:
        """Return top_k chunks without similarity (basic strategy)."""
        sql = (
            "SELECT content, document_source, 0.0 AS cosine_similarity "
            "FROM documents_chunks ORDER BY chunk_id ASC LIMIT %s"
        )
        with self.connect() as conn, conn.cursor() as cur:
            cur.execute(sql, (top_k,))
            rows = cur.fetchall()
            return [(str(r[0]), str(r[1]) if r[1] is not None else "", float(r[2])) for r in rows]

    # Session-scoped operations for retrieving chunks from conversation history index
    def count_session_chunks(self, session_id: str) -> int:
        sql = "SELECT COUNT(*) FROM documents_chunks WHERE document_source = %s"
        with self.connect() as conn, conn.cursor() as cur:
            cur.execute(sql, (f"session:{session_id}",))
            (count,) = cur.fetchone()
            return int(count)

    def search_similar_chunks_for_session(
        self, query_embedding: list[float], top_k: int, session_id: str
    ) -> list[tuple[str, str, float]]:
        sql = (
            "WITH q AS (SELECT %s::vector AS v) "
            "SELECT content, document_source, 1 - (embedding <=> q.v) AS cosine_similarity "
            "FROM documents_chunks, q WHERE document_source = %s "
            "ORDER BY embedding <=> q.v ASC LIMIT %s"
        )
        with self.connect() as conn, conn.cursor() as cur:
            vec = Vector(query_embedding)
            try:
                cur.execute("SET enable_indexscan = off; SET enable_bitmapscan = off;")
            except Exception:
                pass
            cur.execute(sql, (vec, f"session:{session_id}", top_k))
            rows = cur.fetchall()
            return [(str(r[0]), str(r[1]) if r[1] is not None else "", float(r[2])) for r in rows]

    def fetch_top_k_chunks_for_session(self, top_k: int, session_id: str) -> list[tuple[str, str, float]]:
        sql = (
            "SELECT content, document_source, 0.0 AS cosine_similarity FROM documents_chunks "
            "WHERE document_source = %s ORDER BY chunk_id ASC LIMIT %s"
        )
        with self.connect() as conn, conn.cursor() as cur:
            cur.execute(sql, (f"session:{session_id}", top_k))
            rows = cur.fetchall()
            return [(str(r[0]), str(r[1]) if r[1] is not None else "", float(r[2])) for r in rows]
