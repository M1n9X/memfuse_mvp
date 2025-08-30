-- Phase 4: Procedural execution lessons (experience) store

CREATE TABLE IF NOT EXISTS procedural_lessons (
  lesson_id UUID PRIMARY KEY,
  trigger_embedding vector(1024) NOT NULL,
  goal_text TEXT NOT NULL,
  agent TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('success','fail')),
  error TEXT,
  fix_summary TEXT,
  working_params JSONB DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_lessons_agent ON procedural_lessons (agent);
CREATE INDEX IF NOT EXISTS idx_lessons_trigger ON procedural_lessons USING ivfflat (trigger_embedding vector_cosine_ops);
