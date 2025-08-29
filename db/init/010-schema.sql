CREATE TABLE IF NOT EXISTS conversations (
  session_id TEXT NOT NULL,
  round_id INT NOT NULL,
  speaker TEXT NOT NULL CHECK (speaker IN ('user', 'ai')),
  content TEXT NOT NULL,
  timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (session_id, round_id, speaker)
);

-- Document chunks for RAG
CREATE TABLE IF NOT EXISTS documents_chunks (
  chunk_id UUID PRIMARY KEY,
  document_source TEXT,
  content TEXT NOT NULL,
  embedding vector(1024) NOT NULL,
  -- Optional idempotency key for avoiding duplicate inserts of same content per source
  content_hash TEXT
);

CREATE INDEX IF NOT EXISTS idx_documents_chunks_embedding ON documents_chunks USING ivfflat (embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS idx_documents_chunks_source ON documents_chunks (document_source);

-- Ensure idempotency/uniqueness when re-indexing the same content for the same source
ALTER TABLE documents_chunks
  ADD COLUMN IF NOT EXISTS content_hash TEXT;
CREATE UNIQUE INDEX IF NOT EXISTS uniq_documents_source_hash ON documents_chunks (document_source, content_hash);
