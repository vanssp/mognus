"""Week 03: FastAPI + Ollama tool calling classifier."""

from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any

import httpx
import psycopg2
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

load_dotenv()

app = FastAPI(title="week-03 tool calling")

OLLAMA_URL = os.getenv(
    "OLLAMA_URL",
    "http://158.160.217.42:11434/v1/chat/completions",
)
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:1.5b")
DATABASE_URL = os.getenv("DATABASE_URL")

TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "save_to_db",
            "description": "Save message classification to Postgres",
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "enum": ["question", "task", "chitchat", "other"],
                    },
                    "priority": {
                        "type": "string",
                        "enum": ["low", "medium", "high"],
                    },
                    "summary": {"type": "string"},
                },
                "required": ["category", "priority", "summary"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "print_in_stdout",
            "description": "Log current timestamp",
            "parameters": {
                "type": "object",
                "properties": {
                    "message": {"type": "string"},
                },
                "required": ["message"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "notify_telegram",
            "description": "Notify a human about the classification result",
            "parameters": {
                "type": "object",
                "properties": {
                    "message": {"type": "string"},
                },
                "required": ["message"],
            },
        },
    },
]

SYSTEM_PROMPT = (
    "You are a message classifier. "
    "Always call save_to_db with category, priority and summary. "
    "Always call notify_telegram with a short human-readable message. "
    "Always call print_in_stdout with current UTC datetime. "
    "Do not answer with plain text instead of tools."
)


class ClassifyIn(BaseModel):
    text: str = Field(..., min_length=1)


class ClassifyOut(BaseModel):
    category: str
    priority: str
    summary: str
    tool_called: bool
    db_id: int | None = None


def _parse_args(raw: Any) -> dict[str, Any]:
    if raw is None:
        return {}
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        return json.loads(raw)
    raise TypeError(f"Unexpected tool arguments type: {type(raw)}")


def db_save(
    raw_text: str,
    category: str,
    priority: str,
    summary: str,
    llm_raw: str,
) -> int:
    if not DATABASE_URL:
        raise HTTPException(500, "DATABASE_URL is not set")

    conn = psycopg2.connect(DATABASE_URL)
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO webhook_classifications
                        (raw_text, category, priority, summary, llm_raw)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (raw_text, category, priority, summary, llm_raw),
                )
                row = cur.fetchone()
                return int(row[0])
    finally:
        conn.close()


def notify_telegram(message: str) -> dict[str, Any]:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        print("[telegram stub]", message)
        return {"ok": True, "stub": True}

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    with httpx.Client(timeout=30) as client:
        resp = client.post(url, json={"chat_id": chat_id, "text": message})
        resp.raise_for_status()
        return resp.json()


def print_in_stdout(dt: str) -> None:
    print(dt)


@app.get("/health")
def health() -> dict[str, bool]:
    return {"ok": True}


@app.post("/classify", response_model=ClassifyOut)
def classify(body: ClassifyIn) -> ClassifyOut:
    payload = {
        "model": OLLAMA_MODEL,
        "temperature": 0,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Classify message:\n{body.text}"},
        ],
        "tools": TOOLS,
        "tool_choice": "auto",
    }

    try:
        with httpx.Client(timeout=120.0) as client:
            resp = client.post(OLLAMA_URL, json=payload)
    except httpx.RequestError as exc:
        raise HTTPException(502, f"ollama unreachable: {exc}") from exc

    if resp.status_code >= 400:
        raise HTTPException(502, f"ollama error {resp.status_code}: {resp.text}")

    data = resp.json()
    try:
        message = data["choices"][0]["message"]
    except (KeyError, IndexError, TypeError) as exc:
        raise HTTPException(502, f"unexpected ollama response: {data}") from exc

    tool_calls = message.get("tool_calls") or []
    if not tool_calls:
        raise HTTPException(
            status_code=502,
            detail={
                "error": "model_did_not_call_tools",
                "content": message.get("content"),
            },
        )

    saved: dict[str, Any] | None = None
    db_id: int | None = None
    llm_raw = json.dumps(data, ensure_ascii=False)

    for call in tool_calls:
        fn = call.get("function") or {}
        name = fn.get("name")
        args = _parse_args(fn.get("arguments"))

        if name == "save_to_db":
            db_id = db_save(
                raw_text=body.text,
                category=args["category"],
                priority=args["priority"],
                summary=args["summary"],
                llm_raw=llm_raw,
            )
            saved = args
        elif name == "print_in_stdout":
            print_in_stdout(args.get("message"))
        elif name == "notify_telegram":
            notify_telegram(args.get("message") or json.dumps(args, ensure_ascii=False))
        else:
            print(f"[warn] unknown tool: {name}")

    if not saved:
        raise HTTPException(502, "save_to_db was not called")

    return ClassifyOut(
        category=saved["category"],
        priority=saved["priority"],
        summary=saved["summary"],
        tool_called=True,
        db_id=db_id,
    )