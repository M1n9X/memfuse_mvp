-- Phase 4: Procedural (Workflow) Memory schema

CREATE TABLE IF NOT EXISTS procedural_memory (
  workflow_id UUID PRIMARY KEY,
  trigger_embedding vector(1024) NOT NULL,
  trigger_pattern TEXT,
  successful_workflow JSONB NOT NULL,
  usage_count INT NOT NULL DEFAULT 0,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_procedural_trigger ON procedural_memory USING ivfflat (trigger_embedding vector_cosine_ops);

-- Basic maintenance trigger to update updated_at
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_procedural_updated_at ON procedural_memory;
CREATE TRIGGER trg_procedural_updated_at
BEFORE UPDATE ON procedural_memory
FOR EACH ROW EXECUTE FUNCTION set_updated_at();
