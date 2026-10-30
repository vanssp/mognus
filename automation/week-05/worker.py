"""Простой polling-воркер для jobs status=queued."""
from __future__ import annotations
import os
import time
import traceback
import psycopg2
from dotenv import load_dotenv
from psycopg2.extras import Json
from rag import run_ingest


load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
POLL_SEC = float(os.getenv("WORKER_POLL_SEC", "2"))


def db():
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL is not set")
    return psycopg2.connect(DATABASE_URL)


def claim_one_job():
    """Берём одну queued job и сразу ставим running (SKIP LOCKED)."""
    conn = db()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, payload
                    FROM jobs
                    WHERE status = 'queued' AND job_type = 'ingest'
                    ORDER BY created_at
                    FOR UPDATE SKIP LOCKED
                    LIMIT 1
                    """
                )
                row = cur.fetchone()
                if not row:
                    return None
                job_id, payload = row[0], row[1] or {}
                cur.execute(
                    """
                    UPDATE jobs
                    SET status = 'running', updated_at = NOW()
                    WHERE id = %s
                    """,
                    (job_id,),
                )
                return str(job_id), payload
    finally:
        conn.close()


def finish(job_id: str, *, result=None, error: str | None = None) -> None:
    status = "failed" if error else "done"
    conn = db()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE jobs
                    SET status = %s,
                        result = %s,
                        error = %s,
                        updated_at = NOW()
                    WHERE id = %s
                    """,
                    (status, Json(result) if result is not None else None, error, job_id),
                )
    finally:
        conn.close()


def process(job_id: str, payload: dict) -> None:
    print(f"[worker] running job {job_id}")
    try:
        result = run_ingest(
            texts=payload.get("texts") or None,
            reset=bool(payload.get("reset", False)),
        )
        finish(job_id, result=result)
        print(f"[worker] done job {job_id}: {result}")
    except Exception as exc:  # noqa: BLE001
        err = f"{exc}\n{traceback.format_exc()}"
        finish(job_id, error=str(exc))
        print(f"[worker] failed job {job_id}: {err}")


def main() -> None:
    print(f"[worker] started, poll={POLL_SEC}s")
    while True:
        claimed = claim_one_job()
        if claimed is None:
            time.sleep(POLL_SEC)
            continue
        job_id, payload = claimed
        process(job_id, payload if isinstance(payload, dict) else {})


if __name__ == "__main__":
    main()
