"""Week 04: RAG with Ollama embeddings + pgvector + FastAPI."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

import httpx
import psycopg2
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from psycopg2.extras import execute_values

load_dotenv()

app = FastAPI(title="week-04 RAG")

DATABASE_URL = os.getenv("DATABASE_URL")
OLLAMA_BASE = os.getenv("OLLAMA_BASE", "http://158.160.217.42:11434").rstrip("/")
EMBED_MODEL = os.getenv("EMBED_MODEL", "nomic-embed-text")
CHAT_MODEL = os.getenv("CHAT_MODEL", "qwen2.5:1.5b")
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "800"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "120"))
TOP_K = int(os.getenv("TOP_K", "4"))
DOCS_DIR = Path(__file__).resolve().parent / "docs"


class IngestBody(BaseModel):
    """If texts is empty, files from ./docs are ingested."""

    texts: list[dict[str, str]] = Field(
        default_factory=list,
        description='Optional: [{"source": "a.md", "content": "..."}]',
    )
    reset: bool = Field(
        default=False,
        description="If true, wipe documents/chunks before ingest",
    )


class AskBody(BaseModel):
    question: str = Field(..., min_length=1)
    top_k: int | None = None


class SourceOut(BaseModel):
    source: str
    chunk_index: int
    content: str
    score: float | None = None


class AskOut(BaseModel):
    answer: str
    sources: list[SourceOut]


def _db():
    if not DATABASE_URL:
        raise HTTPException(500, "DATABASE_URL is not set")
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
        raise HTTPException(502, f"embed error: {resp.text}")
    data = resp.json()
    vec = data.get("embedding")
    if not vec:
        raise HTTPException(502, f"empty embedding: {data}")
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
        raise HTTPException(502, f"chat error: {resp.text}")
    data = resp.json()
    try:
        return data["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, TypeError, AttributeError) as exc:
        raise HTTPException(502, f"bad chat response: {data}") from exc


def load_docs_from_disk() -> list[dict[str, str]]:
    if not DOCS_DIR.exists():
        return []
    out: list[dict[str, str]] = []
    for path in sorted(DOCS_DIR.rglob("*")):
        if not path.is_file():
            continue
        if path.suffix.lower() not in {".txt", ".md", ".markdown", ".csv"}:
            continue
        out.append({"source": str(path.relative_to(DOCS_DIR)), "content": path.read_text(encoding="utf-8", errors="ignore")})
    return out


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "ok": True,
        "embed_model": EMBED_MODEL,
        "chat_model": CHAT_MODEL,
        "docs_dir": str(DOCS_DIR),
    }


@app.post("/ingest")
def ingest(body: IngestBody) -> dict[str, Any]:
    docs = body.texts or load_docs_from_disk()
    if not docs:
        raise HTTPException(
            400,
            "No documents. Put files into automation/week-04/docs/ or pass texts[].",
        )

    conn = _db()
    inserted_docs = 0
    inserted_chunks = 0
    try:
        with conn:
            with conn.cursor() as cur:
                if body.reset:
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

                    pieces = chunk_text(content)
                    rows: list[tuple[Any, ...]] = []
                    for idx, piece in enumerate(pieces):
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


@app.post("/ask", response_model=AskOut)
def ask(body: AskBody) -> AskOut:
    k = body.top_k or TOP_K
    q_vec = embed(body.question)
    q_lit = vector_literal(q_vec)

    conn = _db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT c.content, d.source, c.chunk_index,
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
        raise HTTPException(404, "No chunks in DB. Call /ingest first.")

    contexts = [r[0] for r in rows]
    answer = chat_with_context(body.question, contexts)
    sources = [
        SourceOut(
            source=r[1],
            chunk_index=int(r[2]),
            content=r[0],
            score=float(r[3]) if r[3] is not None else None,
        )
        for r in rows
    ]
    return AskOut(answer=answer, sources=sources)
