CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS webhook_classifications (
  id         BIGSERIAL PRIMARY KEY,
  raw_text   TEXT NOT NULL,
  category   TEXT,
  priority   TEXT,
  summary    TEXT,
  llm_raw    TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_webhook_classifications_created_at
  ON webhook_classifications (created_at DESC);

CREATE INDEX IF NOT EXISTS idx_webhook_classifications_category
  ON webhook_classifications (category);