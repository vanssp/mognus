# Week 05 — Jobs + Idempotency + RAG evals
Долгий ingest через async jobs (`202` + `job_id`), защита от дублей через `Idempotency-Key`, оценка RAG по golden set (hit-rate / faithfulness-proxy), логирование `/ask`.
## Подготовка БД
Нужны таблицы RAG из week-04 (`db_rag.sql`) **и** jobs:
```bash
docker exec -i mog-postgres psql -U n8n -d automation < automation/week-04/db_rag.sql
docker exec -i mog-postgres psql -U n8n -d automation < automation/week-05/db_jobs.sql
```
## Запуск
```bash
cd automation/week-05
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # поправь DATABASE_URL / OLLAMA_BASE
# API
uvicorn main:app --host 0.0.0.0 --port 8005 --reload
# воркер в другом терминале
python worker.py
```
В `docs/` уже лежат примеры `rag.md` и `week03.md` (можно заменить своими).
## Проверка jobs + идемпотентности
```bash
# 1) создать job
curl -s -D - http://127.0.0.1:8005/jobs/ingest \
  -H 'Content-Type: application/json' \
  -H 'Idempotency-Key: ingest-demo-1' \
  -d '{"reset": true}'
# 2) тот же ключ ещё раз → тот же job_id, idempotent_replay=true
curl -s http://127.0.0.1:8005/jobs/ingest \
  -H 'Content-Type: application/json' \
  -H 'Idempotency-Key: ingest-demo-1' \
  -d '{"reset": true}'
# 3) статус
curl -s http://127.0.0.1:8005/jobs/<JOB_ID>
```
Жди `status: done`, пока воркер крутится.
## Ask + логи
```bash
curl -s http://127.0.0.1:8005/ask \
  -H 'Content-Type: application/json' \
  -d '{"question":"Что такое RAG?"}'
```
Логи пишутся в таблицу `ask_logs` (question, answer, sources, latency_ms).
## Eval (golden set)
```bash
# API должен быть запущен, ingest done
python eval_rag.py
```
Смотри `eval_report.md`: hit-rate, faithfulness-proxy, latency p50/p95.
## Метрики (заполни после прогона)
| Метрика | Значение |
|---------|----------|
| hit-rate | |
| faithfulness-proxy | |
| latency p50 / p95 | |
## Что узнал (для собеса)
- Долгий пайплайн → `202` + `job_id`, статус отдельным GET.
- `Idempotency-Key` не даёт ретраю поднять второй ingest.
- Hit-rate = нужный source в top-k; faithfulness-proxy = ответ опирается на эталонные маркеры / контекст.
- В проде логируем вопрос, sources/score, ответ, latency.