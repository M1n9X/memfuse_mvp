-- API Schema Extensions for FastAPI compatibility
-- This extends the existing schema to support users, agents, sessions, and messages APIs

-- Users table
CREATE TABLE IF NOT EXISTS users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL UNIQUE,
  email TEXT,
  metadata JSONB DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_users_name ON users (name);
CREATE INDEX IF NOT EXISTS idx_users_email ON users (email);

-- Agents table  
CREATE TABLE IF NOT EXISTS agents (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL UNIQUE,
  type TEXT NOT NULL DEFAULT 'assistant',
  description TEXT,
  config JSONB DEFAULT '{}'::jsonb,
  metadata JSONB DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_agents_name ON agents (name);
CREATE INDEX IF NOT EXISTS idx_agents_type ON agents (type);

-- Sessions table (replaces session_id strings with proper relationships)
CREATE TABLE IF NOT EXISTS sessions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  agent_id UUID NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
  name TEXT,
  metadata JSONB DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions (user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_agent ON sessions (agent_id);
CREATE INDEX IF NOT EXISTS idx_sessions_created ON sessions (created_at);

-- Messages table (extends conversations with proper relationships)
CREATE TABLE IF NOT EXISTS messages (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
  role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
  content TEXT NOT NULL,
  metadata JSONB DEFAULT '{}'::jsonb,
  -- Support for M3 workflow logging
  tags TEXT[] DEFAULT '{}',
  workflow_id UUID,
  step_index INTEGER,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_messages_session ON messages (session_id);
CREATE INDEX IF NOT EXISTS idx_messages_role ON messages (role);
CREATE INDEX IF NOT EXISTS idx_messages_created ON messages (created_at);
CREATE INDEX IF NOT EXISTS idx_messages_workflow ON messages (workflow_id);
CREATE INDEX IF NOT EXISTS idx_messages_tags ON messages USING GIN (tags);

-- Migration helper: Create a view to map old session_id strings to new UUIDs
-- This allows gradual migration from string-based sessions to UUID-based sessions
CREATE TABLE IF NOT EXISTS session_mappings (
  old_session_id TEXT PRIMARY KEY,
  new_session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_session_mappings_new ON session_mappings (new_session_id);

-- Function to get or create session mapping
CREATE OR REPLACE FUNCTION get_or_create_session_uuid(
  p_old_session_id TEXT,
  p_user_name TEXT DEFAULT 'default_user',
  p_agent_name TEXT DEFAULT 'memfuse_assistant'
) RETURNS UUID AS $$
DECLARE
  v_session_uuid UUID;
  v_user_id UUID;
  v_agent_id UUID;
BEGIN
  -- Check if mapping already exists
  SELECT new_session_id INTO v_session_uuid 
  FROM session_mappings 
  WHERE old_session_id = p_old_session_id;
  
  IF v_session_uuid IS NOT NULL THEN
    RETURN v_session_uuid;
  END IF;
  
  -- Get or create user
  SELECT id INTO v_user_id FROM users WHERE name = p_user_name;
  IF v_user_id IS NULL THEN
    INSERT INTO users (name) VALUES (p_user_name) RETURNING id INTO v_user_id;
  END IF;
  
  -- Get or create agent
  SELECT id INTO v_agent_id FROM agents WHERE name = p_agent_name;
  IF v_agent_id IS NULL THEN
    INSERT INTO agents (name, type, description) 
    VALUES (p_agent_name, 'assistant', 'MemFuse AI Assistant') 
    RETURNING id INTO v_agent_id;
  END IF;
  
  -- Create new session
  INSERT INTO sessions (user_id, agent_id, name)
  VALUES (v_user_id, v_agent_id, p_old_session_id)
  RETURNING id INTO v_session_uuid;
  
  -- Create mapping
  INSERT INTO session_mappings (old_session_id, new_session_id)
  VALUES (p_old_session_id, v_session_uuid);
  
  RETURN v_session_uuid;
END;
$$ LANGUAGE plpgsql;

-- Update triggers for updated_at columns
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_users_updated_at ON users;
CREATE TRIGGER trg_users_updated_at
  BEFORE UPDATE ON users
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS trg_agents_updated_at ON agents;
CREATE TRIGGER trg_agents_updated_at
  BEFORE UPDATE ON agents
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS trg_sessions_updated_at ON sessions;
CREATE TRIGGER trg_sessions_updated_at
  BEFORE UPDATE ON sessions
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Insert default user and agent for backward compatibility
INSERT INTO users (id, name, email)
VALUES (gen_random_uuid(), 'default_user', 'default@memfuse.ai')
ON CONFLICT (name) DO NOTHING;

INSERT INTO agents (id, name, type, description, config)
VALUES (
  gen_random_uuid(),
  'memfuse_assistant',
  'assistant',
  'MemFuse AI Assistant with layered memory capabilities',
  '{"model": "gpt-4o-mini", "temperature": 0.7}'::jsonb
)
ON CONFLICT (name) DO NOTHING;
