MemFuse MVP - Phase 1

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

Debugging (no LLM call)
```bash
# Inspect retrieval + context sizes without calling the LLM
poetry run memfuse debug session1 "your question here"
```

End-to-end checklist
- Ensure `.env` contains valid keys:
  - `JINA_API_KEY`
  - `OPENAI_API_KEY`, `OPENAI_BASE_URL`, `OPENAI_COMPATIBLE_MODEL`
- Start DB: `docker compose up -d`
- Ingest content: `poetry run memfuse ingest seed ./sample.txt`
- Verify retrieval: `poetry run memfuse debug sess1 "Why did we choose Plan B?"`
- Chat: `poetry run memfuse chat sess1 "Why did we choose Plan B?"`
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

Testing
```bash
poetry run pytest -q
```
