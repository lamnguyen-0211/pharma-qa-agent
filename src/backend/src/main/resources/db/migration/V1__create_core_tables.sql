CREATE TABLE conversation (
  id VARCHAR(36) PRIMARY KEY,
  created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE message (
  id VARCHAR(36) PRIMARY KEY,
  conversation_id VARCHAR(36) NOT NULL REFERENCES conversation(id) ON DELETE CASCADE,
  role VARCHAR(16) NOT NULL CHECK (role IN ('USER', 'ASSISTANT', 'SYSTEM')),
  content TEXT NOT NULL,
  risk_level VARCHAR(16) NOT NULL DEFAULT 'LOW' CHECK (risk_level IN ('LOW', 'MEDIUM', 'HIGH', 'EMERGENCY')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX message_conversation_created_idx ON message (conversation_id, created_at);
CREATE TABLE audit_event (
  id VARCHAR(36) PRIMARY KEY,
  conversation_id VARCHAR(36) REFERENCES conversation(id) ON DELETE SET NULL,
  event_type VARCHAR(64) NOT NULL,
  trace_id VARCHAR(36),
  metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX audit_event_conversation_created_idx ON audit_event (conversation_id, created_at);
