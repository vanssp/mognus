INSERT INTO webhook_classifications (raw_text, category, priority, summary, llm_raw)
VALUES ($1, $2, $3, $4, $5)
RETURNING id, created_at;

-- $1 = {{ $json.text }}
-- $2 = {{ $json.category }}
-- $3 = {{ $json.priority }}
-- $4 = {{ $json.summary }}
-- $5 = {{ $json.llm_raw }}