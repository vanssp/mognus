# Week 03 — FastAPI + LLM tool calling

Сервис классификации сообщений: Ollama вызывает tools, результат пишется в Postgres.

## Что делает

`POST /classify` → Ollama (`qwen2.5:1.5b`) с tool calling →

- `save_to_db` — сохраняет `category` / `priority` / `summary` в `webhook_classifications`
- `notify_telegram` — шлёт уведомление (или stub в stdout, если нет токена)
- `print_in_stdout` — логирует сообщение в консоль

Ответ API: `category`, `priority`, `summary`, `tool_called`, `db_id`.

## Стек

Python 3.12, FastAPI, Uvicorn, httpx, psycopg2-binary, Ollama, PostgreSQL.

## Запуск

```bash
# Postgres (из корня репо)
docker compose up -d postgres

cd automation/week-03
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# заполни DATABASE_URL, при необходимости TELEGRAM_*

uvicorn main:app --host 0.0.0.0 --port 8001 --reload
```

## Проверка

```bash
curl -s http://localhost:8001/health

curl -s http://localhost:8001/classify \
  -H 'Content-Type: application/json' \
  -d '{"text":"Назови столицу Франции"}'
```

Ожидаемый ответ (пример):

```json
{
  "category": "question",
  "priority": "low",
  "summary": "...",
  "tool_called": true,
  "db_id": 1
}
```

Проверка БД:

```sql
SELECT id, raw_text, category, priority, summary, created_at
FROM webhook_classifications
ORDER BY id DESC
LIMIT 5;
```

## Env

Скопируй `.env.example` → `.env`. Не коммить секреты.

| Переменная | Описание |
|---|---|
| `OLLAMA_URL` | OpenAI-compatible endpoint Ollama |
| `OLLAMA_MODEL` | модель с поддержкой tools |
| `DATABASE_URL` | `postgresql://user:pass@localhost:5432/db` |
| `TELEGRAM_BOT_TOKEN` | опционально |
| `TELEGRAM_CHAT_ID` | опционально |

## Интеграция с n8n (бонус)

Из n8n в Docker/K8s: `http://host.docker.internal:8001/classify`  
(uvicorn обязательно с `--host 0.0.0.0`).