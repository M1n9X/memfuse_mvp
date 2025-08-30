#!/usr/bin/env bash
set -euo pipefail

# One-click start for MemFuse DB and schema
# Usage:
#   scripts/start.sh [--reset]

RESET=false
if [[ "${1:-}" == "--reset" ]]; then
  RESET=true
fi

# Load .env if present for POSTGRES_* defaults
if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

export POSTGRES_USER="${POSTGRES_USER:-memfuse}"
export POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-memfuse}"
export POSTGRES_DB="${POSTGRES_DB:-memfuse}"

if $RESET; then
  echo "[MemFuse] Resetting database volume..."
  docker compose down -v || true
fi

echo "[MemFuse] Pulling images..."
docker pull postgres:17
docker pull pgvector/pgvector:pg17

echo "[MemFuse] Starting database..."
docker compose up -d

echo "[MemFuse] Waiting for DB to be ready..."
until docker exec memfuse_db pg_isready -U "${POSTGRES_USER}" >/dev/null 2>&1; do
  sleep 1
  printf '.'
done

echo
# Ensure pgvector extension exists (init scripts should handle it; this is idempotent)
echo "[MemFuse] Ensuring pgvector extension and schema are ready..."
docker exec memfuse_db psql -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" -tAc "CREATE EXTENSION IF NOT EXISTS vector;" >/dev/null 2>&1 || true
# Re-run schema scripts in case of reset or manual image switch
docker exec memfuse_db psql -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" -f /docker-entrypoint-initdb.d/010-schema.sql >/dev/null 2>&1 || true
docker exec memfuse_db psql -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" -f /docker-entrypoint-initdb.d/020-structured-memory.sql >/dev/null 2>&1 || true
docker exec memfuse_db psql -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" -f /docker-entrypoint-initdb.d/030-procedural-memory.sql >/dev/null 2>&1 || true

echo "[MemFuse] DB is ready: ${POSTGRES_USER}@localhost/${POSTGRES_DB}"
