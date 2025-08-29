#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
import uuid
from typing import List

from memfuse.config import Settings
from memfuse.rag import RAGService


def ensure_service() -> RAGService:
    s = Settings.from_env()
    object.__setattr__(s, 'structured_enabled', True)
    object.__setattr__(s, 'extractor_enabled', True)
    object.__setattr__(s, 'extractor_trigger_tokens', 1)
    object.__setattr__(s, 'extractor_dedup_top_k', 10)
    service = RAGService.from_settings(s)
    # Disable networked LLM chat with compatible signature
    class _LLM:
        def chat(self, system_prompt, messages):
            return "ok"
    service.llm = _LLM()
    # Deterministic extractor output: echo back a normalized fact composed from the AI text
    def mock_completion_json(sys_prompt: str, user_prompt: str) -> str:
        # if user_prompt contains the word 'contradict', emit a negative preference; else a positive one
        if 'contradict' in user_prompt:
            return '{"items":[{"type":"User_Preference","content":"User does not like apples"}]}'
        return '{"items":[{"type":"User_Preference","content":"User likes apples"}]}'
    service.extractor.llm.completion_json = mock_completion_json  # type: ignore
    # Empty embeddings to avoid hitting APIs
    service.embedder.embed = lambda texts: [[0.0]*s.embedding_dim for _ in texts]  # type: ignore
    service.extractor.embedder.embed = lambda texts: [[0.0]*s.embedding_dim for _ in texts]  # type: ignore
    return service


def reset_session(service: RAGService, session_id: str) -> None:
    with service.db.connect() as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM structured_memory WHERE session_id=%s", (session_id,))
        cur.execute("DELETE FROM conversations WHERE session_id=%s", (session_id,))


def main() -> int:
    service = ensure_service()
    sess = f"m2_dedup_{uuid.uuid4().hex[:8]}"
    reset_session(service, sess)

    # First: likes apples -> expect an insertion
    service.chat(sess, "He likes apples")
    with service.db.connect() as conn, conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM structured_memory WHERE session_id=%s", (sess,))
        n1 = cur.fetchone()[0]
    if n1 < 1:
        print("FAIL: expected first insertion")
        return 1

    # Second: similar info -> extractor should be allowed to return empty (dedup)
    service.chat(sess, "He likes apples (again)")
    with service.db.connect() as conn, conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM structured_memory WHERE session_id=%s", (sess,))
        n2 = cur.fetchone()[0]
    if n2 != n1:
        print("FAIL: expected no new insertion on dedup")
        return 2

    # Third: contradiction -> mock returns negative; expect insertion and earlier rounds marked extracted as well
    service.chat(sess, "contradict: He does not like apples now")
    with service.db.connect() as conn, conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM structured_memory WHERE session_id=%s", (sess,))
        n3 = cur.fetchone()[0]
    if n3 != n1 + 1:
        print("FAIL: expected insertion for contradiction")
        return 3

    print("ALL OK")
    return 0


if __name__ == '__main__':
    sys.exit(main())
