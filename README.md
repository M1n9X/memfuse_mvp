MemFuse MVP - Phase 1 → Phase 4 Ready

Prerequisites
- Poetry (Python 3.11)
- Docker

Setup
1. Copy .env.example to .env and fill secrets.
2. Pull base images (optional but recommended):
   ```bash
   docker pull postgres:17
   docker pull pgvector/pgvector:pg17
   ```
3. Install dependencies:
   ```bash
   poetry install
   ```
4. Start Postgres with pgvector:
   ```bash
   docker compose up -d
   ```

One-click start
```bash
# Start or reset-and-start DB + schema
scripts/start.sh         # normal start
scripts/start.sh --reset # drop volumes then start
```

Usage
- Ingest a text file:
  ```bash
  poetry run memfuse ingest mydoc ./path/to/file.txt
  ```
- Chat:
  ```bash
  # Single-turn
  poetry run memfuse chat session1 "What did we discuss at the start?"
  # Interactive terminal chatbot
  poetry run memfuse chat session1 -
  # If using an OpenAI-compatible endpoint, ensure env values:
  #   OPENAI_BASE_URL, OPENAI_API_KEY, OPENAI_COMPATIBLE_MODEL
  ```

Phase 2 (Structured Memory) quick start
- Enable M2 in `.env`:
  ```bash
  STRUCTURED_ENABLED=true
  EXTRACTOR_ENABLED=true
  ```
- Ensure DB is (re)initialized with structured schema:
  ```bash
  scripts/start.sh --reset
  ```
- Verify extractor batching and flags:
  ```bash
  poetry run python scripts/test_m2_extractor.py
  ```
- Verify facts recall path (vector search over structured facts):
  ```bash
  poetry run python scripts/test_facts_recall.py
  ```

Phase 3 (Multi-Agent) quick start
- Orchestrated tasks:
  ```bash
  poetry run memfuse task sess1 "Analyze sample data and draft a report"
  # Interactive orchestrator
  poetry run memfuse task sess1 -
  ```

Phase 4 (Procedural Memory) quick start
- Enable M3 in `.env`:
  ```bash
  M3_ENABLED=true
  PROCEDURAL_REUSE_THRESHOLD=0.9
  ```
- After a successful orchestrated run, the workflow is learned and stored.
- Subsequent similar goals will be fast-pathed via reuse if similarity ≥ threshold.

Notes on performance & robustness
- Ingestion and session indexing are idempotent by content hash. Re-ingesting or re-chatting will not duplicate vector rows.
- DB schema creates a unique index on `(document_source, content_hash)` under `documents_chunks`.
- You can control DB-side history fetch window via `HISTORY_FETCH_ROUNDS` (default 200). Fine-grained token truncation is still handled by the context controller using `HISTORY_MAX_TOKENS`.
- Retrieval behavior can be tuned with `RETRIEVAL_PREFER_SESSION` (default true). If true and session index exists, retrieval prefers session-scoped chunks; otherwise uses global corpus.

Schema changes & migration
- If you created the DB volume before this version, run:
  ```bash
  scripts/start.sh --reset
  ```
  to recreate schema and apply the unique index and M3 schema.

Debugging (no LLM call)
```bash
# Inspect retrieval + context sizes without calling the LLM
poetry run memfuse debug session1 "your question here"
```

Health check
```bash
# Quick checks (DB connectivity, optional live API pings)
poetry run memfuse health --strict --check-embeddings --check-llm
```

End-to-end checklist
- Ensure `.env` contains valid keys:
  - `JINA_API_KEY`
  - `OPENAI_API_KEY`, `OPENAI_BASE_URL`, `OPENAI_COMPATIBLE_MODEL`
- Start DB: `docker compose up -d`
- Ingest content: `poetry run memfuse ingest seed ./sample.txt`
- Verify retrieval: `poetry run memfuse debug sess1 "Why did we choose Plan B?"`
- Chat: `poetry run memfuse chat sess1 "Why did we choose Plan B?"`
- (M2) Verify extractor & structured recall:
  - `poetry run python scripts/test_m2_extractor.py`
  - `poetry run python scripts/test_m2_dedup_contradiction.py`
- Verify memory persisted (optional):
  ```bash
  docker exec memfuse_db psql -U ${POSTGRES_USER:-memfuse} -d ${POSTGRES_DB:-memfuse} -c \
    "SELECT session_id, round_id, speaker, left(content,60) FROM conversations ORDER BY timestamp DESC LIMIT 10;"
  ```

Notes
- Context limits per PRD:
  - `USER_INPUT_MAX_TOKENS` default lowered for demo
  - `TOTAL_CONTEXT_MAX_TOKENS` default lowered for demo
  - `HISTORY_MAX_TOKENS` controls how much history is included
- Retrieval ordering uses cosine similarity on pgvector.
- If retrieval ever returns 0 unexpectedly with very small datasets, the code falls back to sequential scan (disables index/bitmap scan) to avoid ivfflat edge-cases during MVP.
 - Structured retrieval merges exact-ish facts (by vector/keywords) with unstructured chunks first, aligning with PRD Stage 2.

Testing
```bash
poetry run pytest -q
```

End-to-end scripts
```bash
# Start DB
scripts/start.sh
# E2E for Phase 3
poetry run python scripts/e2e_phase3.py
# E2E for Phase 4 (requires M3_ENABLED=true and valid keys)
poetry run python scripts/e2e_phase4.py
```
