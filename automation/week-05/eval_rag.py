"""Прогон golden set: hit-rate + простой faithfulness-proxy."""
from __future__ import annotations
import json
import os
import statistics
import time
from pathlib import Path
import httpx
from dotenv import load_dotenv

load_dotenv()

BASE = os.getenv("ASK_BASE_URL", "http://127.0.0.1:8005").rstrip("/")
GOLDEN = Path(__file__).resolve().parent / "golden_set.json"
REPORT = Path(__file__).resolve().parent / "eval_report.md"


def hit(sources: list[dict], expected_sources: list[str]) -> bool:
    got = {str(s.get("source", "")).lower() for s in sources}
    exp = {e.lower() for e in expected_sources}
    return bool(got & exp)


def faithful_proxy(answer: str, needles: list[str], was_hit: bool) -> bool:
    """Грубая проверка без LLM-judge."""
    text = (answer or "").lower()
    if any(n.lower() in text for n in needles):
        return True
    # если retrieval miss и модель честно не знает — считаем ок-ish
    if not was_hit and ("не знаю" in text or "don't know" in text):
        return True
    return False


def main() -> None:
    items = json.loads(GOLDEN.read_text(encoding="utf-8"))
    rows = []
    latencies: list[float] = []
    hits = 0
    faithful = 0
    with httpx.Client(timeout=180.0) as client:
        for item in items:
            q = item["question"]
            t0 = time.perf_counter()
            resp = client.post(f"{BASE}/ask", json={"question": q})
            elapsed = (time.perf_counter() - t0) * 1000
            latencies.append(elapsed)
            if resp.status_code >= 400:
                rows.append(
                    {
                        "id": item["id"],
                        "hit": False,
                        "faithful": False,
                        "error": resp.text,
                        "latency_ms": round(elapsed, 1),
                    }
                )
                continue
            data = resp.json()
            sources = data.get("sources") or []
            answer = data.get("answer") or ""
            is_hit = hit(sources, item.get("expected_sources") or [])
            is_f = faithful_proxy(answer, item.get("expected_answer_contains") or [], is_hit)
            hits += int(is_hit)
            faithful += int(is_f)
            rows.append(
                {
                    "id": item["id"],
                    "hit": is_hit,
                    "faithful": is_f,
                    "sources": [s.get("source") for s in sources],
                    "answer": answer[:200],
                    "latency_ms": round(elapsed, 1),
                }
            )
    n = len(items) or 1
    p50 = statistics.median(latencies) if latencies else 0
    p95 = sorted(latencies)[max(0, int(len(latencies) * 0.95) - 1)] if latencies else 0
    lines = [
        "# Week 05 eval report",
        "",
        f"- questions: {len(items)}",
        f"- hit-rate: {hits}/{len(items)} ({hits / n:.0%})",
        f"- faithfulness-proxy: {faithful}/{len(items)} ({faithful / n:.0%})",
        f"- latency_ms p50: {p50:.0f}",
        f"- latency_ms p95: {p95:.0f}",
        "",
        "## Details",
        "```json",
        json.dumps(rows, ensure_ascii=False, indent=2),
        "```",
        "",
    ]
    REPORT.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines[:8]))
    print(f"saved: {REPORT}")


if __name__ == "__main__":
    main()
