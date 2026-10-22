# Week 02 — линия классификации

Webhook → Ollama → Validate → IF → Postgres + Telegram (fail → Telegram).

| | Было | Стало |
|--|------|-------|
| Разбор 1 сообщения | ~2–3 мин вручную | ~3–10 сек автоматом |
| Результат | никуда | Postgres + Telegram |
| Плохой LLM | ломал процесс | ветка fail → алерт |

Стек: n8n, Ollama qwen2.5:1.5b, PostgreSQL, Telegram.  
Проверка: Active + `curl` на `/webhook/practice` → строка в PG + Telegram.