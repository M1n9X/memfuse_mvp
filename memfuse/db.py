from __future__ import annotations

import contextlib
from dataclasses import dataclass
from typing import Iterator, Optional, List, Tuple

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
        self, chunk_id: str, document_source: str, content: str, embedding: list[float], content_hash: str | None = None
    ) -> None:
        with self.connect() as conn, conn.cursor() as cur:
            if content_hash is None:
                cur.execute(
                    "INSERT INTO documents_chunks (chunk_id, document_source, content, embedding) "
                    "VALUES (%s, %s, %s, %s)",
                    (chunk_id, document_source, content, embedding),
                )
            else:
                cur.execute(
                    "INSERT INTO documents_chunks (chunk_id, document_source, content, embedding, content_hash) "
                    "VALUES (%s, %s, %s, %s, %s) "
                    "ON CONFLICT (document_source, content_hash) DO NOTHING",
                    (chunk_id, document_source, content, embedding, content_hash),
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

    # ----- Extraction coordination helpers (Phase 2) -----
    def fetch_unextracted_rounds(self, session_id: str) -> list[tuple[int, str, str]]:
        """Return list of (round_id, user_content, ai_content) for rounds where AI row is not extracted yet."""
        sql = (
            "SELECT c.round_id, c.speaker, c.content FROM conversations c "
            "WHERE c.session_id = %s AND c.round_id IN ("
            "  SELECT round_id FROM conversations WHERE session_id = %s AND speaker='ai' AND is_extracted = FALSE"
            ") ORDER BY c.round_id ASC, c.timestamp ASC"
        )
        with self.connect() as conn, conn.cursor() as cur:
            cur.execute(sql, (session_id, session_id))
            rows = cur.fetchall()
        # Group by round_id
        by_round: dict[int, dict[str, str]] = {}
        for rid, spk, content in rows:
            rd = by_round.setdefault(int(rid), {"user": "", "ai": ""})
            rd[str(spk)] = str(content)
        result: list[tuple[int, str, str]] = []
        for rid in sorted(by_round.keys()):
            rd = by_round[rid]
            result.append((rid, rd.get("user", ""), rd.get("ai", "")))
        return result

    def mark_rounds_extracted(self, session_id: str, round_ids: list[int]) -> int:
        if not round_ids:
            return 0
        # Use ANY array to avoid IN expansion complexities
        sql = (
            "UPDATE conversations SET is_extracted = TRUE WHERE session_id = %s "
            "AND round_id = ANY(%s)"
        )
        with self.connect() as conn, conn.cursor() as cur:
            cur.execute(sql, (session_id, round_ids))
            return cur.rowcount or 0

    # ----- Phase 2: Structured memory operations -----
    def insert_structured_records(
        self,
        records: List[Tuple[str, str, int, str, str, dict, dict, List[float] | None]],
    ) -> int:
        """Bulk insert structured memory records.

        Each record tuple is (fact_id, session_id, source_round_id, type, content, relations, metadata)
        Returns number of rows inserted (ignores conflicts by primary key if any).
        """
        if not records:
            return 0
        sql = (
            "INSERT INTO structured_memory (fact_id, session_id, source_round_id, type, content, relations, metadata, embedding) "
            "VALUES (%s, %s, %s, %s, %s, %s::jsonb, %s::jsonb, %s) "
            "ON CONFLICT (fact_id) DO NOTHING"
        )
        with self.connect() as conn, conn.cursor() as cur:
            inserted = 0
            for rec in records:
                # convert dicts to JSON strings for psycopg
                r0, r1, r2, r3, r4, r5, r6, r7 = rec
                rel_json = psycopg.types.json.Json(r5)
                meta_json = psycopg.types.json.Json(r6)
                try:
                    cur.execute(sql, (r0, r1, r2, r3, r4, rel_json, meta_json, r7))
                except Exception as e:
                    # Fallback if 'embedding' column doesn't exist in current DB
                    if "embedding" in str(e) and "column" in str(e).lower():
                        cur.execute(
                            "INSERT INTO structured_memory (fact_id, session_id, source_round_id, type, content, relations, metadata) "
                            "VALUES (%s, %s, %s, %s, %s, %s::jsonb, %s::jsonb) ON CONFLICT (fact_id) DO NOTHING",
                            (r0, r1, r2, r3, r4, rel_json, meta_json),
                        )
                    else:
                        raise
                inserted += cur.rowcount if cur.rowcount is not None else 1
            return inserted

    def query_structured_by_keywords(
        self, session_id: str, keywords: List[str], top_k: int
    ) -> List[Tuple[str, str, float]]:
        """Simple keyword search over `structured_memory.content` for the session.

        Returns list of (content, source, pseudo_score). Source will be like "structured:{type}#round".
        Pseudo score is number of keyword matches.
        """
        if not keywords:
            return []
        # Build ILIKE conditions
        conditions = " OR ".join(["content ILIKE %s" for _ in keywords])
        params: List[object] = [session_id] + [f"%{kw}%" for kw in keywords]
        sql = (
            "SELECT content, type, source_round_id "
            f"FROM structured_memory WHERE session_id = %s AND ({conditions})"
        )
        with self.connect() as conn, conn.cursor() as cur:
            cur.execute(sql, tuple(params))
            rows = cur.fetchall()
            # rank by number of matched keywords
            results: List[Tuple[str, str, float]] = []
            for content, typ, rid in rows:
                text = str(content)
                score = sum(1 for kw in keywords if kw.lower() in text.lower())
                source = f"structured:{str(typ)}#round={int(rid)}"
                results.append((text, source, float(score)))
            # sort desc by score and truncate
            results.sort(key=lambda r: r[2], reverse=True)
            return results[:top_k]

    def fetch_structured_recent_for_session(self, session_id: str, top_k: int) -> List[Tuple[str, str, float]]:
        """Fetch recent structured items for session to provide context (ordered by created_at DESC)."""
        sql = (
            "SELECT content, type, source_round_id FROM structured_memory "
            "WHERE session_id = %s ORDER BY created_at DESC LIMIT %s"
        )
        with self.connect() as conn, conn.cursor() as cur:
            cur.execute(sql, (session_id, top_k))
            rows = cur.fetchall()
            return [(str(r[0]), f"structured:{str(r[1])}#round={int(r[2])}", 0.0) for r in rows]

    def query_structured_similar(
        self, session_id: str, query_embedding: List[float], top_k: int
    ) -> List[Tuple[str, str, float]]:
        """Vector similarity search over structured facts for dedup/contradiction detection."""
        sql = (
            "WITH q AS (SELECT %s::vector AS v) "
            "SELECT content, type, source_round_id, 1 - (embedding <=> q.v) AS cosine_similarity "
            "FROM structured_memory, q WHERE session_id = %s AND embedding IS NOT NULL "
            "ORDER BY embedding <=> q.v ASC LIMIT %s"
        )
        with self.connect() as conn, conn.cursor() as cur:
            vec = Vector(query_embedding)
            try:
                cur.execute("SET enable_indexscan = off; SET enable_bitmapscan = off;")
            except Exception:
                pass
            cur.execute(sql, (vec, session_id, top_k))
            rows = cur.fetchall()
            return [(str(r[0]), f"structured:{str(r[1])}#round={int(r[2])}", float(r[3])) for r in rows]

    # ----- Phase 4: Procedural memory operations -----
    def upsert_procedural_workflow(
        self,
        workflow_id: str,
        trigger_embedding: List[float],
        successful_workflow: dict,
        trigger_pattern: Optional[str] = None,
    ) -> None:
        sql = (
            "INSERT INTO procedural_memory (workflow_id, trigger_embedding, trigger_pattern, successful_workflow, usage_count) "
            "VALUES (%s, %s, %s, %s::jsonb, 1) "
            "ON CONFLICT (workflow_id) DO UPDATE SET "
            "trigger_embedding = EXCLUDED.trigger_embedding, "
            "trigger_pattern = EXCLUDED.trigger_pattern, "
            "successful_workflow = EXCLUDED.successful_workflow, "
            "usage_count = procedural_memory.usage_count + 1"
        )
        with self.connect() as conn, conn.cursor() as cur:
            vec = Vector(trigger_embedding)
            cur.execute(sql, (workflow_id, vec, trigger_pattern, psycopg.types.json.Json(successful_workflow)))

    def query_procedural_similar(self, query_embedding: List[float], top_k: int) -> List[Tuple[str, dict, float]]:
        """Return list of (workflow_id, successful_workflow_json, cosine_similarity)."""
        sql = (
            "WITH q AS (SELECT %s::vector AS v) "
            "SELECT workflow_id, successful_workflow, 1 - (trigger_embedding <=> q.v) AS cosine_similarity "
            "FROM procedural_memory, q ORDER BY trigger_embedding <=> q.v ASC LIMIT %s"
        )
        with self.connect() as conn, conn.cursor() as cur:
            vec = Vector(query_embedding)
            try:
                cur.execute("SET enable_indexscan = off; SET enable_bitmapscan = off;")
            except Exception:
                pass
            cur.execute(sql, (vec, top_k))
            rows = cur.fetchall()
            results: List[Tuple[str, dict, float]] = []
            for wid, wf_json, score in rows:
                try:
                    wf = wf_json if isinstance(wf_json, dict) else wf_json  # psycopg returns python object
                except Exception:
                    wf = {}
                results.append((str(wid), wf, float(score)))
            return results

    def bump_procedural_usage(self, workflow_id: str, by: int = 1) -> int:
        with self.connect() as conn, conn.cursor() as cur:
            cur.execute("UPDATE procedural_memory SET usage_count = usage_count + %s WHERE workflow_id = %s", (by, workflow_id))
            return cur.rowcount or 0
