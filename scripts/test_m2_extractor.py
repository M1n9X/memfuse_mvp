#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
import time
import uuid
from typing import List, Tuple

from memfuse.config import Settings
from memfuse.rag import RAGService
from memfuse.tokenizer import count_tokens


def ensure_service() -> RAGService:
    settings = Settings.from_env()
    # Force-enable Phase 2 features for the test (without changing user's .env)
    object.__setattr__(settings, 'structured_enabled', True)
    object.__setattr__(settings, 'extractor_enabled', True)
    object.__setattr__(settings, 'extractor_trigger_tokens', int(os.getenv('EXTRACTOR_TRIGGER_TOKENS', '2000')))
    service = RAGService.from_settings(settings)

    # Stub external calls for determinism
    # 1) LLM (chat) should not hit network
    service.llm.chat = lambda system_prompt, messages: "ok"

    # 2) Extractor JSON completion should be deterministic and unique per insertion to avoid unique index conflicts
    counter = {'i': 0}

    def mock_completion_json(system_prompt: str, user_prompt: str) -> str:
        counter['i'] += 1
        # embed a unique token so (session_id, type, content) stays unique across calls
        unique = f"{counter['i']}-{int(time.time()*1000)}"
        return '{"items":[{"type":"Decision","content":"auto-fact-'+unique+'"}]}'

    service.extractor.llm.completion_json = mock_completion_json  # type: ignore

    # 3) Embeddings: return a fixed-dim zero vector deterministically
    def mock_embed(texts: List[str]) -> List[List[float]]:
        return [[0.0] * settings.embedding_dim for _ in texts]

    service.embedder.embed = mock_embed  # type: ignore
    service.extractor.embedder.embed = mock_embed  # type: ignore

    return service


def reset_session(service: RAGService, session_id: str) -> None:
    with service.db.connect() as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM structured_memory WHERE session_id=%s", (session_id,))
        cur.execute("DELETE FROM documents_chunks WHERE document_source=%s", (f"session:{session_id}",))
        cur.execute("DELETE FROM conversations WHERE session_id=%s", (session_id,))


def make_text_for_tokens(target_tokens: int) -> str:
    # Build a text whose token count is >= target_tokens using a simple repeated token
    # Adjust adaptively based on tiktoken count
    base = "x"
    words: List[str] = []
    # pre-allocate a rough size to reduce iterations
    step = max(10, target_tokens // 10)
    while count_tokens(" ".join(words)) < target_tokens:
        words.extend([base] * step)
    # Trim down if we overshoot too much
    text = " ".join(words)
    # ensure we do not overshoot ridiculously; it is acceptable to exceed a little
    return text


def query_structured_count(service: RAGService, session_id: str) -> int:
    with service.db.connect() as conn, conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM structured_memory WHERE session_id=%s", (session_id,))
        (n,) = cur.fetchone()
        return int(n)


def query_round_flags(service: RAGService, session_id: str) -> List[Tuple[int, bool]]:
    with service.db.connect() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT round_id, is_extracted FROM conversations WHERE session_id=%s AND speaker='ai' ORDER BY round_id ASC",
            (session_id,),
        )
        rows = cur.fetchall()
        return [(int(r[0]), bool(r[1])) for r in rows]


def test_case_large_round_triggers(service: RAGService, threshold: int) -> None:
    session = f"m2_large_{uuid.uuid4().hex[:8]}"
    reset_session(service, session)
    # Build a user query that alone exceeds threshold
    user_q = make_text_for_tokens(threshold + 100)
    # Sanity check token count
    assert count_tokens(user_q) >= threshold
    # Chat once -> should trigger extraction immediately for round 1
    service.chat(session, user_q)

    n = query_structured_count(service, session)
    flags = dict(query_round_flags(service, session))
    assert n >= 1, f"Expected >=1 structured items inserted for session {session}, got {n}"
    assert flags.get(1) is True, f"Expected round 1 marked extracted, got flags={flags}"
    print(f"OK large_round_triggers: structured={n}, flags={flags}")


def test_case_accumulate_then_trigger(service: RAGService, threshold: int) -> None:
    session = f"m2_acc_{uuid.uuid4().hex[:8]}"
    reset_session(service, session)

    # Create several small rounds that are below threshold cumulatively, then one that crosses
    small = max(50, threshold // 20)  # 20 small rounds ~ threshold
    texts: List[str] = []
    token_sums: List[int] = []
    total = 0
    # Add 5 small rounds first (should not trigger)
    for _ in range(5):
        t = make_text_for_tokens(small)
        texts.append(t)
        total += count_tokens(t)
        token_sums.append(total)
        service.chat(session, t)
        assert query_structured_count(service, session) == 0, "Structured should still be empty before reaching threshold"
    # Now add rounds until we reach/exceed threshold
    rounds_added = 0
    while total < threshold:
        t = make_text_for_tokens(small)
        texts.append(t)
        total += count_tokens(t)
        token_sums.append(total)
        service.chat(session, t)
        rounds_added += 1
    n = query_structured_count(service, session)
    flags = dict(query_round_flags(service, session))
    assert n >= 1, f"Expected >=1 structured items after crossing threshold; got {n}"
    # At least first N rounds included should be marked extracted (batch accumulates from oldest, marks both user and ai rows)
    # Compute minimal prefix reaching threshold
    prefix_sum = 0
    included = 0
    for i, t in enumerate(texts, start=1):
        prefix_sum += count_tokens(t)
        included = i
        if prefix_sum >= threshold:
            break
    for rid in range(1, included + 1):
        assert flags.get(rid) is True, f"Expected round {rid} extracted in batch; flags={flags}"
    print(f"OK accumulate_then_trigger: structured={n}, included_rounds=1..{included}, flags={flags}")


def main() -> int:
    try:
        service = ensure_service()
        # Quick DB ping by opening/closing a connection
        with service.db.connect() as _:
            pass
    except Exception as e:
        print(f"FAIL setup: {e}")
        return 2

    threshold = service.settings.extractor_trigger_tokens

    try:
        test_case_large_round_triggers(service, threshold)
        test_case_accumulate_then_trigger(service, threshold)
    except AssertionError as e:
        print(f"FAIL: {e}")
        return 1
    except Exception as e:
        print(f"FAIL unexpected: {e}")
        return 3

    print("ALL OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
