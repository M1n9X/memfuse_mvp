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

Usage
- Ingest a text file:
  ```bash
  poetry run memfuse ingest mydoc ./path/to/file.txt
  ```
- Chat:
  ```bash
  poetry run memfuse chat session1 "What did we discuss at the start?"
  # If using an OpenAI-compatible endpoint, ensure env values:
  #   OPENAI_BASE_URL, OPENAI_API_KEY, OPENAI_COMPATIBLE_MODEL
  ```

Testing
```bash
poetry run pytest -q
```
