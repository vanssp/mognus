# mognus

Story / nutrition API (FastAPI + Ollama + frontend) и линия AI-автоматизации на n8n.

Android-игра «могну» («кто кого могнет») лежит в каталоге [`android/`](android/README.md).

## Стек приложения

- `backend/` — FastAPI (`/generate`)
- `frontend/` — Vite/React
- `ollama` — локальная модель (`qwen2.5:1.5b`)

```bash
docker compose up -d --build