const content = $json.choices?.[0]?.message?.content ?? "";
const cleaned = String(content).replace(/```json|```/g, "").trim();

let ok = false;
let parsed = null;
let reason = "";

if (!cleaned) {
  reason = "empty_content";
} else {
  try {
    parsed = JSON.parse(cleaned);
    const cats = ["question", "task", "chitchat", "other"];
    const pris = ["low", "medium", "high"];
    if (!cats.includes(parsed.category)) reason = "bad_category";
    else if (!pris.includes(parsed.priority)) reason = "bad_priority";
    else if (!parsed.summary || String(parsed.summary).length < 2) reason = "bad_summary";
    else ok = true;
  } catch (e) {
    reason = "invalid_json";
  }
}

const text = $("Edit Fields").item.json.text;

return [{
  json: {
    llm_ok: ok,
    reason: reason || "ok",
    category: parsed?.category ?? null,
    priority: parsed?.priority ?? null,
    summary: parsed?.summary ?? null,
    llm_raw: content,
    text,
  },
}];