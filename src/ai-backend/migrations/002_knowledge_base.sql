CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS knowledge_document (
  id UUID PRIMARY KEY,
  checksum CHAR(64) NOT NULL UNIQUE,
  original_filename VARCHAR(255) NOT NULL,
  media_type VARCHAR(100) NOT NULL,
  source_bytes BYTEA NOT NULL,
  byte_size INTEGER NOT NULL CHECK (byte_size > 0),
  title VARCHAR(255) NOT NULL,
  document_type VARCHAR(100) NOT NULL,
  product VARCHAR(255),
  active_ingredient VARCHAR(255),
  market VARCHAR(100),
  jurisdiction VARCHAR(100),
  language VARCHAR(32) NOT NULL,
  effective_date DATE,
  expiration_date DATE,
  version VARCHAR(64) NOT NULL,
  approval_status VARCHAR(32) NOT NULL,
  audience VARCHAR(100),
  access_classification VARCHAR(100) NOT NULL,
  embedding_model_name VARCHAR(255) NOT NULL,
  embedding_dimension INTEGER NOT NULL,
  chunk_count INTEGER NOT NULL CHECK (chunk_count > 0),
  created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CHECK (
    expiration_date IS NULL
    OR effective_date IS NULL
    OR expiration_date >= effective_date
  )
);

CREATE TABLE IF NOT EXISTS knowledge_chunk (
  id UUID PRIMARY KEY,
  document_id UUID NOT NULL REFERENCES knowledge_document(id) ON DELETE CASCADE,
  ordinal INTEGER NOT NULL,
  source_page INTEGER,
  content TEXT NOT NULL,
  textsearch TSVECTOR GENERATED ALWAYS AS (to_tsvector('simple', content)) STORED,
  embedding VECTOR(1024) NOT NULL,
  UNIQUE(document_id, ordinal)
);

CREATE INDEX IF NOT EXISTS knowledge_chunk_embedding_hnsw_idx
  ON knowledge_chunk USING hnsw (embedding vector_cosine_ops);

CREATE INDEX IF NOT EXISTS knowledge_chunk_textsearch_gin_idx
  ON knowledge_chunk USING gin (textsearch);

CREATE INDEX IF NOT EXISTS knowledge_document_eligibility_idx
  ON knowledge_document (approval_status, effective_date, expiration_date);
