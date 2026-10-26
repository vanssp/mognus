# RAG

RAG (Retrieval-Augmented Generation) — сначала поиск релевантных кусков документов,
потом генерация ответа LLM только по найденному контексту.

Embeddings: nomic-embed-text (вектор размерности 768).
Хранилище: PostgreSQL + расширение pgvector.
Чат-модель: qwen2.5:1.5b.