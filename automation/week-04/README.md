# Week 04 — RAG (pgvector + Ollama)
Пайплайн: chunking → embeddings (`nomic-embed-text`) → pgvector → top-k → LLM (`qwen2.5:1.5b`) → ответ + sources.
## Подготовка БД
Образ Postgres: `pgvector/pgvector:pg16`.
Выполни SQL из `db_rag.sql` (один раз):
```bash
docker exec -i mog-postgres psql -U n8n -d automation < automation/week-04/db_rag.sql
```
(логин/БД подставь свои из `.env`)
## Документы
Положи `.txt` / `.md` в `automation/week-04/docs/` (20–50 файлов или меньше для старта).
## Запуск
```bash
cd automation/week-04
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # поправь DATABASE_URL
uvicorn main:app --host 0.0.0.0 --port 8002 --reload
```
## API
```bash
# индекс (из папки docs)
curl -s localhost:8002/ingest -H 'Content-Type: application/json' -d '{"reset": true}'
# вопрос
curl -s localhost:8002/ask \
  -H 'Content-Type: application/json' \
  -d '{"question":"Что делает week-03?"}'
```
Ответ:
```json
{
  "answer": "...",
  "sources": [
    {"source": "week03.md", "chunk_index": 0, "content": "...", "score": 0.81}
  ]
}
```
## Метрика (для сдачи)
Составь таблицу из ~20 вопросов в этом README: вопрос / верный ответ? / нашёлся источник?