-- Phase 2: Structured (Semantic) Memory schema

-- Create enum-like constraint via CHECK for portability
CREATE TABLE IF NOT EXISTS structured_memory (
  fact_id UUID PRIMARY KEY,
  session_id TEXT NOT NULL,
  source_round_id INT NOT NULL,
  type TEXT NOT NULL CHECK (type IN ('Fact', 'Decision', 'Assumption', 'User_Preference')),
  content TEXT NOT NULL,
  relations JSONB DEFAULT '{}'::jsonb,
  metadata JSONB DEFAULT '{}'::jsonb,
  embedding vector(1024),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_structured_memory_session ON structured_memory (session_id);
CREATE INDEX IF NOT EXISTS idx_structured_memory_round ON structured_memory (session_id, source_round_id);
CREATE INDEX IF NOT EXISTS idx_structured_memory_type ON structured_memory (type);
-- JSONB indexes (optional but helpful)
CREATE INDEX IF NOT EXISTS idx_structured_memory_relations ON structured_memory USING GIN (relations);
CREATE INDEX IF NOT EXISTS idx_structured_memory_metadata ON structured_memory USING GIN (metadata);
CREATE INDEX IF NOT EXISTS idx_structured_memory_embedding ON structured_memory USING ivfflat (embedding vector_cosine_ops);

-- Simple deduplication: avoid inserting identical (session_id, type, content) more than once
CREATE UNIQUE INDEX IF NOT EXISTS uniq_structured_session_type_content
  ON structured_memory (session_id, type, content);
