"""A3 extract: per-child facts, each with an exact quoted span from its source line.

Structured rows (attendance, assessments) become facts deterministically. Free text
(WhatsApp, coach form notes) goes to the local model. Every quote is then checked against
the stored line text: the stored quote is always a real substring of the source, or the
fact is dropped.
"""

import re

from rapidfuzz import fuzz

from ti.extract.prompts import SYSTEM, prompt

TYPES = {"praise", "participation", "concern", "injury", "absence", "other"}


def _fmt_day(iso: str) -> str:
    y, m, d = iso.split("-")
    months = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()
    return f"{int(d)} {months[int(m) - 1]}"


def structured_facts(line) -> list[dict]:
    """Facts from one attendance or assessment row. The quote is the whole row."""
    m = line.meta
    if line.kind == "attendance":
        return [{"name": m["name"], "type": "attendance", "date": d, "quote": line.text,
                 "summary": f"{'Present' if mark == 'P' else 'Absent'} on {_fmt_day(d)}",
                 "value": {"mark": mark}, "extractor": "rule"}
                for d, mark in m["marks"].items() if mark in ("P", "A")]
    if line.kind == "assessment":
        vals = {k: m[k] for k in ("sprint_50m_s", "broad_jump_cm", "run_600m_s")}
        if any(v is None for v in vals.values()):
            return [{"name": m["name"], "type": "assessment", "date": m["date"],
                     "quote": line.text,
                     "summary": f"{m['round'].capitalize()} test: no results recorded",
                     "value": {"round": m["round"], "missing": True}, "extractor": "rule"}]
        return [{"name": m["name"], "type": "assessment", "date": m["date"], "quote": line.text,
                 "summary": (f"{m['round'].capitalize()} test: 50m {vals['sprint_50m_s']:g}s, "
                             f"jump {vals['broad_jump_cm']:g}cm, 600m {vals['run_600m_s']:g}s"),
                 "value": {"round": m["round"], **vals}, "extractor": "rule"}]
    return []


def find_span(needle: str, text: str) -> str | None:
    """Return the exact substring of text that needle refers to, or None.

    Exact match first, then case-insensitive, then a fuzzy alignment (>= 85) for quotes
    the model garbled slightly. The result is always copied out of text itself.
    """
    if not needle:
        return None
    if needle in text:
        return needle
    i = text.lower().find(needle.lower())
    if i >= 0:
        return text[i:i + len(needle)]
    if len(needle) < 8:
        return None
    al = fuzz.partial_ratio_alignment(needle, text, score_cutoff=85)
    if al is None:
        return None
    span = text[al.dest_start:al.dest_end].strip(" ,.")
    return span or None


def _whole_words(span: str, text: str) -> str:
    """Grow a span to whole-word boundaries ("Siddhart" -> "Siddharth")."""
    i = text.find(span)
    j = i + len(span)
    while i > 0 and text[i - 1].isalnum():
        i -= 1
    while j < len(text) and text[j].isalnum():
        j += 1
    return text[i:j]


def _clause_with(name: str, text: str) -> str | None:
    for part in re.split(r"(?<=[.!?])\s+", text):
        if name in part:
            return part.strip()
    return None


def verify(fact: dict, text: str) -> dict | None:
    """Pin name and quote to exact spans of text. None means the fact is rejected."""
    name = find_span(str(fact.get("name", "")).strip(), text) \
        if len(str(fact.get("name", ""))) >= 3 else None
    if name is None:
        return None
    name = _whole_words(name, text)
    quote = find_span(str(fact.get("quote", "")).strip(), text)
    if quote is None or name not in quote:
        quote = _clause_with(name, text)
    if quote is None:
        return None
    ftype = fact.get("type") if fact.get("type") in TYPES else "other"
    summary = str(fact.get("summary") or quote).strip()
    return {"name": name, "type": ftype, "quote": quote, "summary": summary,
            "value": {}, "extractor": "llm"}


def llm_facts(line, client) -> tuple[list[dict], int]:
    """Facts from one free-text line. Returns (verified facts, number rejected)."""
    out = client.generate_json(prompt(line.text), SYSTEM)
    raw = out.get("facts", []) if isinstance(out, dict) else []
    facts, rejected = [], 0
    seen = set()
    for f in raw if isinstance(raw, list) else []:
        if not isinstance(f, dict):
            rejected += 1
            continue
        v = verify(f, line.text)
        if v is None:
            rejected += 1
            continue
        key = (v["name"], v["type"], v["quote"])
        if key in seen:
            continue
        seen.add(key)
        v["date"] = line.meta.get("date")
        facts.append(v)
    return facts, rejected


def extract_line(line, client) -> tuple[list[dict], int]:
    if line.kind in ("attendance", "assessment"):
        return structured_facts(line), 0
    if line.kind in ("whatsapp", "coach_form") and line.text.strip():
        return llm_facts(line, client)
    return [], 0
