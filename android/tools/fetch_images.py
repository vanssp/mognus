# -*- coding: utf-8 -*-
"""Download freely licensed creature photos and build questions.json.

Sources: English Wikipedia lead/page images and Wikimedia Commons search.
Keeps CC BY, CC BY-SA, CC0, GFDL, and public domain. Skips NC, ND,
illustrations, diagrams, and tiny files.
"""

from __future__ import annotations

import json
import re
import sys
import threading
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageOps

from pairs import MAIN, SPARES, _check

ROOT = Path(__file__).resolve().parents[1]
IMG_DIR = ROOT / "app" / "src" / "main" / "assets" / "images"
ASSET_DIR = ROOT / "app" / "src" / "main" / "assets"
CREDIT_PATH = ROOT / "CREDITS.md"
STATE_PATH = Path(__file__).resolve().parent / "credits-state.json"
CACHE_DIR = Path("/tmp/mognu-img-cache")

UA = (
    "MognuAssetBot/1.0 (https://github.com/vanssp/mognus; "
    "educational Android game; Wikimedia Commons photos)"
)
MIN_EDGE = 640
WORKERS = 6

BAD_RES = tuple(
    re.compile(pattern, re.I)
    for pattern in (
        r"\bdiagram\b",
        r"\bicon\b",
        r"\blocator\b",
        r"\bskeleton\b",
        r"\bskull\b",
        r"\bdrawing\b",
        r"\billustration\b",
        r"\bpainting\b",
        r"\bengraving\b",
        r"\bstamp\b",
        r"\bwatermark\b",
        r"\blogo\b",
        r"\bflag of\b",
        r"coat of arms",
        r"range map",
        r"distribution map",
        r"\bschematic\b",
        r"\breconstruction\b",
        r"\bartwork\b",
        r"\bsketch\b",
        r"\bfossil\b",
        r"\bcarcass\b",
        r"\bkilled\b",
        r"\bdissection\b",
        r"\btrophy\b",
        r"\bbutcher\b",
        r"\bblood\b",
        r"\bdead\b",
        r"\bpostage\b",
        r"\bheraldry\b",
        r"\breplica\b",
        r"\bstatue\b",
        r"\bmonument\b",
    )
)
STATE_LOCK = threading.Lock()


def slug(wiki: str) -> str:
    text = unicodedata.normalize("NFKD", wiki)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower()
    return (text or "creature")[:70]


def get_json(url: str, params: dict | None = None, timeout: int = 40) -> dict | None:
    if params:
        url = url + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            if exc.code in (429, 503, 502) and attempt < 3:
                time.sleep(1.5 * (attempt + 1))
                continue
            if exc.code == 404:
                return None
            if attempt < 3:
                time.sleep(0.8 * (attempt + 1))
                continue
            return None
        except Exception:
            if attempt < 3:
                time.sleep(0.8 * (attempt + 1))
                continue
            return None
    return None


def download(url: str) -> bytes | None:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=50) as resp:
                data = resp.read()
            if len(data) < 4000:
                return None
            return data
        except Exception:
            time.sleep(0.7 * (attempt + 1))
    return None


def license_text(meta: dict) -> str:
    parts = []
    for key in ("LicenseShortName", "License", "UsageTerms"):
        raw = ((meta.get(key) or {}).get("value") or "")
        parts.append(re.sub(r"<[^>]+>", " ", raw))
    return " ".join(parts)


def license_ok(text: str) -> bool:
    s = (text or "").lower()
    if not s.strip():
        return False
    if any(b in s for b in ("noncommercial", "non-commercial", "by-nc", "by nc", "-nc", "noderiv", "no derivatives", "by-nd")):
        return False
    good = (
        "public domain", "cc0", "cc-zero", "cc by", "cc-by",
        "gfdl", "gnu free documentation", "no restrictions",
    )
    return any(g in s for g in good)


def looks_bad(name: str, categories: list[str]) -> bool:
    blob = name + " " + " ".join(categories)
    return any(pattern.search(blob) for pattern in BAD_RES)


def file_title_from_url(url: str) -> str:
    name = urllib.parse.unquote(url.split("?")[0].rstrip("/").split("/")[-1])
    if name.startswith("File:"):
        return name
    return "File:" + name


def meta_for_files(titles: list[str]) -> list[dict]:
    if not titles:
        return []
    found: list[dict] = []
    for endpoint in (
        "https://en.wikipedia.org/w/api.php",
        "https://commons.wikimedia.org/w/api.php",
    ):
        missing_next: list[str] = []
        for i in range(0, len(titles), 8):
            chunk = titles[i : i + 8]
            data = get_json(
                endpoint,
                {
                    "action": "query",
                    "format": "json",
                    "titles": "|".join(chunk),
                    "prop": "imageinfo|categories",
                    "iiprop": "url|size|mime|extmetadata",
                    "iiurlwidth": "1400",
                    "cllimit": "30",
                    "redirects": "1",
                },
            )
            if not data:
                missing_next.extend(chunk)
                continue
            pages = (data.get("query") or {}).get("pages") or {}
            seen = set()
            for page in pages.values():
                title = page.get("title") or ""
                seen.add(title)
                info = (page.get("imageinfo") or [None])[0]
                if not info:
                    if title:
                        missing_next.append(title)
                    continue
                meta = info.get("extmetadata") or {}
                license_name = license_text(meta)
                cats = [c.get("title", "") for c in page.get("categories") or []]
                mime = info.get("mime") or ""
                width = int(info.get("width") or 0)
                height = int(info.get("height") or 0)
                original = info.get("url") or ""
                thumb = info.get("thumburl") or original
                if not original or not mime.startswith("image/"):
                    continue
                if mime in ("image/svg+xml", "image/gif"):
                    continue
                if max(width, height) < MIN_EDGE:
                    continue
                if not license_ok(license_name):
                    continue
                if looks_bad(title, cats):
                    continue
                short_name = re.sub(
                    r"<[^>]+>",
                    "",
                    ((meta.get("LicenseShortName") or {}).get("value") or ""),
                ).strip()
                short = short_name or re.sub(r"\s+", " ", license_name).strip()[:80]
                host = "commons.wikimedia.org" if "upload.wikimedia.org" in original else "en.wikipedia.org"
                found.append(
                    {
                        "title": title,
                        "url": thumb or original,
                        "original": original,
                        "width": width,
                        "height": height,
                        "license": short[:80],
                        "page": f"https://{host}/wiki/"
                        + urllib.parse.quote(title.replace(" ", "_"), safe=":/()'"),
                        "score": min(width, 2400) + (80 if mime == "image/jpeg" else 0),
                    }
                )
            for name in chunk:
                if name not in seen and name not in missing_next:
                    missing_next.append(name)
        titles = [name for name in missing_next if name]
        if found or not titles:
            break
    # Prefer the widest distinct files.
    uniq = {}
    for item in found:
        prev = uniq.get(item["title"])
        if prev is None or item["score"] > prev["score"]:
            uniq[item["title"]] = item
    return list(uniq.values())


def wiki_page_files(title: str) -> list[str]:
    data = get_json(
        "https://en.wikipedia.org/w/api.php",
        {
            "action": "query",
            "format": "json",
            "titles": title,
            "prop": "images",
            "imlimit": "40",
            "redirects": "1",
        },
    )
    if not data:
        return []
    pages = (data.get("query") or {}).get("pages") or {}
    titles = []
    for page in pages.values():
        if "missing" in page:
            continue
        for img in page.get("images") or []:
            name = img.get("title") or ""
            if name.lower().endswith((".svg", ".gif", ".tif", ".tiff")):
                continue
            titles.append(name)
    return titles


def commons_search(query: str) -> list[dict]:
    data = get_json(
        "https://commons.wikimedia.org/w/api.php",
        {
            "action": "query",
            "format": "json",
            "generator": "search",
            "gsrsearch": f"{query} photograph",
            "gsrnamespace": "6",
            "gsrlimit": "12",
            "prop": "imageinfo|categories",
            "iiprop": "url|size|mime|extmetadata",
            "iiurlwidth": "1400",
            "cllimit": "20",
        },
    )
    if not data:
        return []
    pages = (data.get("query") or {}).get("pages") or {}
    titles = [p.get("title") for p in pages.values() if p.get("title")]
    # The generator response already includes imageinfo; reuse meta_for_files
    # only if the embedded info is thin. Re-query for a consistent shape.
    return meta_for_files(titles)


def resolve_wiki_title(title: str) -> str | None:
    data = get_json(
        "https://en.wikipedia.org/api/rest_v1/page/summary/"
        + urllib.parse.quote(title, safe="")
    )
    if data and data.get("title") and data.get("type") != "disambiguation":
        return data["title"]
    search = get_json(
        "https://en.wikipedia.org/w/api.php",
        {
            "action": "opensearch",
            "search": title,
            "limit": "1",
            "namespace": "0",
            "format": "json",
        },
    )
    if search and len(search) > 1 and search[1]:
        return search[1][0]
    return None


def lead_candidate(title: str) -> dict | None:
    data = get_json(
        "https://en.wikipedia.org/w/api.php",
        {
            "action": "query",
            "format": "json",
            "titles": title,
            "prop": "pageimages",
            "piprop": "name|original",
            "redirects": "1",
        },
    )
    if not data:
        return None
    pages = (data.get("query") or {}).get("pages") or {}
    if not pages:
        return None
    page = next(iter(pages.values()))
    name = page.get("pageimage")
    if not name:
        return None
    metas = meta_for_files(["File:" + name.replace("_", " ")])
    if not metas:
        metas = meta_for_files(["File:" + name])
    return metas[0] if metas else None


def title_tokens(title: str) -> list[str]:
    skip = {"animal", "genus", "common", "species", "the", "with"}
    return [
        token.lower()
        for token in re.split(r"[^A-Za-z0-9]+", title)
        if len(token) > 3 and token.lower() not in skip
    ]


def best_photo(wiki: str) -> dict | None:
    title = resolve_wiki_title(wiki) or wiki
    lead = lead_candidate(title)
    if lead:
        return lead
    tokens = title_tokens(title)
    candidates = meta_for_files(wiki_page_files(title))
    if tokens:
        candidates = [
            item for item in candidates if any(token in item["title"].lower() for token in tokens)
        ]
    if not candidates:
        candidates = commons_search(title)
    if not candidates and title != wiki:
        candidates = commons_search(wiki)
    if not candidates:
        return None
    candidates.sort(key=lambda item: item["score"], reverse=True)
    return candidates[0]


def to_webp(raw: bytes) -> bytes | None:
    try:
        im = Image.open(BytesIO(raw))
        im = ImageOps.exif_transpose(im)
        if im.mode not in ("RGB", "L"):
            im = im.convert("RGB")
        else:
            im = im.convert("RGB")
        im.thumbnail((720, 720), Image.Resampling.LANCZOS)
        if max(im.size) < 320:
            return None
        chosen = None
        for quality in (82, 76, 70, 64, 58, 52, 46):
            buf = BytesIO()
            im.save(buf, "WEBP", quality=quality, method=6)
            chosen = buf.getvalue()
            if len(chosen) <= 80_000:
                break
        if chosen and len(chosen) > 100_000:
            smaller = im.copy()
            smaller.thumbnail((600, 600), Image.Resampling.LANCZOS)
            buf = BytesIO()
            smaller.save(buf, "WEBP", quality=58, method=6)
            chosen = buf.getvalue()
        if not chosen or len(chosen) < 8_000:
            # Simple micrographs can be small; keep them if the bitmap is real.
            if chosen and len(chosen) >= 4_000:
                return chosen
            return None
        return chosen
    except Exception:
        return None


def fetch_one(ru: str, wiki: str) -> dict | None:
    name = slug(wiki)
    photo = best_photo(wiki)
    if not photo:
        return None
    raw = download(photo["original"] or photo["url"])
    if raw is None and photo.get("url"):
        raw = download(photo["url"])
    if not raw:
        return None
    webp = to_webp(raw)
    if not webp:
        return None
    path = IMG_DIR / f"{name}.webp"
    path.write_bytes(webp)
    return {
        "ru": ru,
        "wiki": wiki,
        "file": f"{name}.webp",
        "bytes": len(webp),
        "license": photo["license"],
        "source": photo["page"],
        "width": photo["width"],
        "height": photo["height"],
    }


def load_state() -> dict:
    if STATE_PATH.exists():
        return json.loads(STATE_PATH.read_text("utf-8"))
    return {}


def save_state(state: dict) -> None:
    STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2), "utf-8")


def side_for(index: int) -> str:
    # Irregular but fixed: the winner is on the bottom a bit under half the time.
    return "b" if ((index * 7 + 3) % 5) < 2 else "a"


def build_questions(ok: dict[str, dict]) -> tuple[list[dict], list[str], list[str]]:
    questions = []
    dropped = []
    used_spare = []
    pool = [("main", row) for row in MAIN] + [("spare", row) for row in SPARES]
    for kind, row in pool:
        strong_ru, strong_wiki, weak_ru, weak_wiki, explanation = row
        if strong_wiki not in ok or weak_wiki not in ok:
            if kind == "main":
                missing = []
                if strong_wiki not in ok:
                    missing.append(strong_ru)
                if weak_wiki not in ok:
                    missing.append(weak_ru)
                dropped.append(f"{strong_ru} / {weak_ru} (нет фото: {', '.join(missing)})")
            continue
        if kind == "spare":
            if len(questions) >= 200:
                break
            used_spare.append(f"{strong_ru} / {weak_ru}")
        if len(questions) >= 200 and kind == "main":
            continue
        index = len(questions) + 1
        a_ru, a_wiki = strong_ru, strong_wiki
        b_ru, b_wiki = weak_ru, weak_wiki
        winner = side_for(index)
        if winner == "b":
            a_ru, a_wiki, b_ru, b_wiki = b_ru, b_wiki, a_ru, a_wiki
        questions.append(
            {
                "id": index,
                "nameA": a_ru,
                "nameB": b_ru,
                "winner": winner,
                "explanation": explanation,
                "imageA": ok[a_wiki]["file"],
                "imageB": ok[b_wiki]["file"],
            }
        )
        if len(questions) >= 200:
            break
    return questions, dropped, used_spare


def write_credits(ok: dict[str, dict], questions: list[dict]) -> None:
    used = set()
    for q in questions:
        used.add(q["imageA"])
        used.add(q["imageB"])
    rows = [item for item in ok.values() if item["file"] in used]
    rows.sort(key=lambda item: item["ru"])
    lines = [
        "# Источники изображений",
        "",
        "Фотографии взяты из Википедии и Wikimedia Commons.",
        "В игре только свободные лицензии: CC BY, CC BY-SA, CC0, GFDL или общественное достояние.",
        "Файлы уменьшены (длинная сторона около 720 пикселей) и сохранены как WebP.",
        "",
        "| Существо | Файл | Страница источника | Лицензия |",
        "| --- | --- | --- | --- |",
    ]
    for item in rows:
        lines.append(
            f"| {item['ru']} | `{item['file']}` | {item['source']} | {item['license']} |"
        )
    lines.append("")
    CREDIT_PATH.write_text("\n".join(lines), "utf-8")


def main() -> int:
    _check()
    IMG_DIR.mkdir(parents=True, exist_ok=True)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    state = load_state()
    creatures: dict[str, str] = {}
    for row in MAIN + SPARES:
        creatures[row[1]] = row[0]
        creatures[row[3]] = row[2]

    pending = []
    for wiki, ru in creatures.items():
        file_name = slug(wiki) + ".webp"
        prev = state.get(wiki)
        if prev and (IMG_DIR / prev["file"]).exists():
            continue
        pending.append((ru, wiki))

    print(f"creatures={len(creatures)} pending={len(pending)} cached={len(creatures)-len(pending)}", flush=True)
    done = 0
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futures = {pool.submit(fetch_one, ru, wiki): wiki for ru, wiki in pending}
        for fut in as_completed(futures):
            wiki = futures[fut]
            done += 1
            try:
                result = fut.result()
            except Exception as exc:
                result = None
                print(f"ERR {wiki}: {exc}", flush=True)
            if result:
                with STATE_LOCK:
                    state[wiki] = result
                    save_state(state)
                print(f"[{done}/{len(pending)}] OK {result['ru']} {result['bytes']}B {result['license']}", flush=True)
            else:
                with STATE_LOCK:
                    state.pop(wiki, None)
                print(f"[{done}/{len(pending)}] FAIL {wiki}", flush=True)
    save_state(state)

    ok = {wiki: item for wiki, item in state.items() if (IMG_DIR / item["file"]).exists()}
    questions, dropped, used_spare = build_questions(ok)
    (ASSET_DIR / "questions.json").write_text(
        json.dumps(questions, ensure_ascii=False, indent=2), "utf-8"
    )
    write_credits(ok, questions)
    report = ROOT / "tools" / "image-report.json"
    report.write_text(
        json.dumps(
            {
                "pairs": len(questions),
                "images": len({q["imageA"] for q in questions} | {q["imageB"] for q in questions}),
                "dropped": dropped,
                "spares_used": used_spare,
                "failed": sorted(set(creatures) - set(ok)),
            },
            ensure_ascii=False,
            indent=2,
        ),
        "utf-8",
    )
    print(
        f"PAIRS {len(questions)} IMAGES {len({q['imageA'] for q in questions} | {q['imageB'] for q in questions})} "
        f"DROPPED {len(dropped)} SPARES {len(used_spare)}",
        flush=True,
    )
    return 0 if len(questions) >= 180 else 1


if __name__ == "__main__":
    sys.exit(main())
