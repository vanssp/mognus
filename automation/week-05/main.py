"""Week 05: jobs API + idempotency + /ask with logging."""
from __future__ import annotations
import json
import os
import time
import uuid
from typing import Any
import psycopg2
from dotenv import load_dotenv

from fastapi import FastAPI, Header, HTTPException, Response
from pydantic import BaseModel, Field
from psycopg2.extras import Json

from rag import run_ask

load_dotenv()
app = FastAPI(title="week-05 jobs + rag evals")
DATABASE_URL = os.getenv("DATABASE_URL")


class IngestJobBody(BaseModel):
    reset: bool = False
    texts: list[dict[str, str]] = Field(default_factory=list)


class AskBody(BaseModel):
    question: str = Field(..., min_length=1)
    top_k: int | None = None


def _db():
    if not DATABASE_URL:
        raise HTTPException(500, "DATABASE_URL is not set")
    return psycopg2.connect(DATABASE_URL)


@app.get("/health")
def health() -> dict[str, str]:
    return {"ok": "true", "service": "week-05"}


@app.post("/jobs/ingest", status_code=202)
def create_ingest_job(
    body: IngestJobBody,
    response: Response,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> dict[str, Any]:
    if not idempotency_key or not idempotency_key.strip():
        raise HTTPException(400, "Header Idempotency-Key is required")
    key = idempotency_key.strip()
    payload = body.model_dump()
    conn = _db()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id, status FROM jobs WHERE idempotency_key = %s",
                    (key,),
                )
                row = cur.fetchone()
                if row:
                    # тот же ключ → тот же job, второй прогон не стартует
                    response.status_code = 202
                    return {
                        "job_id": str(row[0]),
                        "status": row[1],
                        "idempotent_replay": True,
                    }
                job_id = uuid.uuid4()
                cur.execute(
                    """
                    INSERT INTO jobs (id, idempotency_key, job_type, status, payload)
                    VALUES (%s, %s, 'ingest', 'queued', %s)
                    """,
                    (str(job_id), key, Json(payload)),
                )
    except psycopg2.Error as exc:
        raise HTTPException(500, f"db error: {exc}") from exc
    finally:
        conn.close()
    return {"job_id": str(job_id), "status": "queued", "idempotent_replay": False}


@app.get("/jobs/{job_id}")
def get_job(job_id: str) -> dict[str, Any]:
    conn = _db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, idempotency_key, job_type, status, result, error,
                       created_at, updated_at
                FROM jobs WHERE id = %s
                """,
                (job_id,),
            )
            row = cur.fetchone()
    finally:
        conn.close()
    if not row:
        raise HTTPException(404, "job not found")
    return {
        "job_id": str(row[0]),
        "idempotency_key": row[1],
        "job_type": row[2],
        "status": row[3],
        "result": row[4],
        "error": row[5],
        "created_at": row[6].isoformat() if row[6] else None,
        "updated_at": row[7].isoformat() if row[7] else None,
    }


@app.post("/ask")
def ask(body: AskBody) -> dict[str, Any]:
    t0 = time.perf_counter()
    try:
        out = run_ask(body.question, top_k=body.top_k)
    except RuntimeError as exc:
        raise HTTPException(400, str(exc)) from exc
    latency_ms = int((time.perf_counter() - t0) * 1000)
    sources = out["sources"]
    answer = out["answer"]
    conn = _db()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO ask_logs (question, answer, sources, latency_ms)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (body.question, answer, Json(sources), latency_ms),
                )
    finally:
        conn.close()
    return {
        "answer": answer,
        "sources": sources,
        "latency_ms": latency_ms,
    }
