"""Shared RAG helpers (упрощённый перенос из week-04)."""
from __future__ import annotations
import os
import re
from pathlib import Path
from typing import Any
import httpx
import psycopg2
from psycopg2.extras import execute_values


DATABASE_URL = os.getenv("DATABASE_URL")
OLLAMA_BASE = os.getenv("OLLAMA_BASE", "http://127.0.0.1:11434").rstrip("/")
EMBED_MODEL = os.getenv("EMBED_MODEL", "nomic-embed-text")
CHAT_MODEL = os.getenv("CHAT_MODEL", "qwen2.5:1.5b")
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "800"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "120"))
TOP_K = int(os.getenv("TOP_K", "4"))
DOCS_DIR = Path(__file__).resolve().parent / "docs"


def db():
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL is not set")
    return psycopg2.connect(DATABASE_URL)


def chunk_text(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return []
    if len(text) <= size:
        return [text]
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + size, len(text))
        piece = text[start:end].strip()
        if piece:
            chunks.append(piece)
        if end >= len(text):
            break
        start = max(0, end - overlap)
    return chunks


def embed(text: str) -> list[float]:
    url = f"{OLLAMA_BASE}/api/embeddings"
    with httpx.Client(timeout=120.0) as client:
        resp = client.post(url, json={"model": EMBED_MODEL, "prompt": text})
    if resp.status_code >= 400:
        raise RuntimeError(f"embed error: {resp.text}")
    vec = resp.json().get("embedding")
    if not vec:
        raise RuntimeError("empty embedding")
    return vec


def vector_literal(vec: list[float]) -> str:
    return "[" + ",".join(f"{x:.8f}" for x in vec) + "]"


def chat_with_context(question: str, contexts: list[str]) -> str:
    context_block = "\n\n".join(f"[{i + 1}] {c}" for i, c in enumerate(contexts))
    system = (
        "You answer ONLY using the provided context. "
        "If the context is insufficient, say you don't know. "
        "Answer in Russian. Be concise."
    )
    user = f"Context:\n{context_block}\n\nQuestion: {question}"
    url = f"{OLLAMA_BASE}/v1/chat/completions"
    payload = {
        "model": CHAT_MODEL,
        "temperature": 0,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    }
    with httpx.Client(timeout=180.0) as client:
        resp = client.post(url, json=payload)
    if resp.status_code >= 400:
        raise RuntimeError(f"chat error: {resp.text}")
    data = resp.json()
    return data["choices"][0]["message"]["content"].strip()


def load_docs_from_disk() -> list[dict[str, str]]:
    if not DOCS_DIR.exists():
        return []
    out: list[dict[str, str]] = []
    for path in sorted(DOCS_DIR.rglob("*")):
        if not path.is_file():
            continue
        if path.suffix.lower() not in {".txt", ".md", ".markdown"}:
            continue
        out.append(
            {
                "source": str(path.relative_to(DOCS_DIR)),
                "content": path.read_text(encoding="utf-8", errors="ignore"),
            }
        )
    return out


def run_ingest(*, texts: list[dict[str, str]] | None = None, reset: bool = False) -> dict[str, Any]:
    docs = texts or load_docs_from_disk()
    if not docs:
        raise RuntimeError("No documents to ingest")
    conn = db()
    inserted_docs = 0
    inserted_chunks = 0
    try:
        with conn:
            with conn.cursor() as cur:
                if reset:
                    cur.execute("TRUNCATE documents RESTART IDENTITY CASCADE")
                for doc in docs:
                    source = doc.get("source") or "untitled"
                    content = (doc.get("content") or "").strip()
                    if not content:
                        continue
                    cur.execute(
                        "INSERT INTO documents (source, content) VALUES (%s, %s) RETURNING id",
                        (source, content),
                    )
                    doc_id = cur.fetchone()[0]
                    inserted_docs += 1
                    rows: list[tuple[Any, ...]] = []
                    for idx, piece in enumerate(chunk_text(content)):
                        vec = embed(piece)
                        rows.append((doc_id, idx, piece, vector_literal(vec)))
                    if rows:
                        execute_values(
                            cur,
                            """
                            INSERT INTO chunks (document_id, chunk_index, content, embedding)
                            VALUES %s

                                                    """,
                            rows,
                            template="(%s, %s, %s, %s::vector)",
                        )
                        inserted_chunks += len(rows)
    finally:
        conn.close()

    return {
        "documents": inserted_docs,
        "chunks": inserted_chunks,
        "chunk_size": CHUNK_SIZE,
        "chunk_overlap": CHUNK_OVERLAP,
    }


def run_ask(question: str, top_k: int | None = None) -> dict[str, Any]:
    k = top_k or TOP_K
    q_lit = vector_literal(embed(question))
    conn = db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT c.id, c.content, d.source, c.chunk_index,
                       1 - (c.embedding <=> %s::vector) AS score
                FROM chunks c
                JOIN documents d ON d.id = c.document_id
                ORDER BY c.embedding <=> %s::vector
                LIMIT %s
                """,
                (q_lit, q_lit, k),
            )
            rows = cur.fetchall()
    finally:
        conn.close()
    if not rows:
        raise RuntimeError("No chunks in DB. Run ingest first.")
    contexts = [r[1] for r in rows]
    answer = chat_with_context(question, contexts)
    sources = [
        {
            "chunk_id": int(r[0]),
            "content": r[1],
            "source": r[2],
            "chunk_index": int(r[3]),
            "score": float(r[4]) if r[4] is not None else None,
        }
        for r in rows
    ]
    return {"answer": answer, "sources": sources}
