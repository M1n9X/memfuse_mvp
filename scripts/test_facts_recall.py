#!/usr/bin/env python3
from __future__ import annotations

"""
Deterministic Facts Recall Test

This script:
1) Ensures a clean session.
2) Inserts a known structured fact (with embedding) for that session.
3) Runs a chat turn and captures the context trace.
4) Asserts that facts are recalled (retrieved_facts_count > 0) and prints the retrieved block.

Run:
  poetry run python scripts/test_facts_recall.py

If this fails with 0 facts:
- Ensure DB schema includes `structured_memory.embedding` (run scripts/start.sh --reset)
- Ensure STRUCTURED_ENABLED=true in .env (or rely on local overrides here)
"""

import os
import sys
import uuid
from typing import List, Tuple

from memfuse.config import Settings
from memfuse.rag import RAGService
from memfuse.tracing import ContextTrace


def ensure_service() -> RAGService:
    s = Settings.from_env()
    # Force enable structured features for testing
    object.__setattr__(s, 'structured_enabled', True)
    object.__setattr__(s, 'extractor_enabled', True)
    object.__setattr__(s, 'structured_top_k', max(5, (s.rag_top_k or 5) * 2))
    service = RAGService.from_settings(s)
    # Avoid networked chat calls
    class _LLM:
        def chat(self, system_prompt, messages):
            return "ok"
    service.llm = _LLM()
    return service


def reset_session(service: RAGService, session_id: str) -> None:
    with service.db.connect() as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM structured_memory WHERE session_id=%s", (session_id,))
        cur.execute("DELETE FROM conversations WHERE session_id=%s", (session_id,))
        cur.execute("DELETE FROM documents_chunks WHERE document_source=%s", (f"session:{session_id}",))


def insert_fact(service: RAGService, session_id: str, round_id: int, content: str, fact_type: str = "Fact") -> None:
    # Create a deterministic embedding for the fact content
    dim = service.settings.embedding_dim
    # Use embedder if available; otherwise construct a simple vector
    try:
        vecs = service.embedder.embed([content])
        vec = vecs[0] if vecs and len(vecs[0]) == dim else [0.0] * dim
    except Exception:
        vec = [0.0] * dim
    rec = [
        (
            str(uuid.uuid4()),
            session_id,
            round_id,
            fact_type,
            content,
            {},
            {"confidence": 0.95},
            vec,
        )
    ]
    inserted = service.db.insert_structured_records(rec)
    if inserted < 1:
        raise RuntimeError("Failed to insert structured fact (check DB schema and permissions)")


def run_recall(service: RAGService, session_id: str, query: str) -> Tuple[int, str]:
    # Run a chat with trace to capture retrieved facts/chunks
    trace = ContextTrace()
    try:
        service.chat(session_id, query, trace=trace)
    except Exception as e:
        print(f"Chat failed: {e}")
        raise
    return trace.retrieved_facts_count, trace.retrieved_block_content or ""


def main() -> int:
    service = ensure_service()
    sess = f"facts_recall_{uuid.uuid4().hex[:8]}"
    reset_session(service, sess)

    # Insert a known Chinese fact and an English fact for recall testing
    insert_fact(service, sess, 1, "用户喜欢苹果", "User_Preference")
    insert_fact(service, sess, 2, "The project uses PostgreSQL with pgvector", "Fact")

    # Ask in Chinese to prefer recalling the Chinese fact
    facts_count, block = run_recall(service, sess, "请问我们是否有人喜欢苹果？")
    print("facts_count=", facts_count)
    print("retrieved block:\n", block)

    if facts_count < 1:
        print("FAIL: expected at least 1 fact recalled")
        return 1

    print("ALL OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
