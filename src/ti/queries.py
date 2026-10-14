"""Read layer shared by the coordinator view (A8) and the API (A7).

Shows only what the decision needs: first name, class, state and cited facts.
No scores or rankings of children are exposed. The store holds pseudonymised text; the
original wording comes from the local private copy when it is on this machine.
"""

import json
import re

from ti.link import REVIEW_MIN
from ti.store import private
from ti.state import STATES


def _meta(conn) -> dict:
    return {k: json.loads(v) for k, v in conn.execute("SELECT key, value FROM run_meta")}


def _originals(conn) -> dict:
    return private.load(_meta(conn).get("private_copy"))


def school_overview(conn) -> dict:
    rows = conn.execute(
        "SELECT c.child_id, c.first, c.class, s.state, s.reason, "
        "(SELECT COUNT(*) FROM facts f WHERE f.child_id = c.child_id) AS n_facts "
        "FROM children c JOIN child_states s USING (child_id) ORDER BY c.first").fetchall()
    groups = {s: [] for s in STATES}
    for r in rows:
        groups[r["state"]].append({
            "child_id": r["child_id"], "first": r["first"], "class": r["class"],
            "reasons": json.loads(r["reason"]), "n_facts": r["n_facts"]})
    review = conn.execute("SELECT COUNT(*) FROM mentions WHERE status = 'review'").fetchone()[0]
    return {"meta": _meta(conn), "groups": groups, "review_open": review}


def _fact_row(r, orig: dict | None = None) -> dict:
    o = (orig or {}).get("facts", {}).get(r["fact_id"], {})
    return {"fact_id": r["fact_id"], "type": r["type"], "date": r["date"],
            "quote": o.get("quote", r["quote"]), "summary": o.get("summary", r["summary"]),
            "stored_quote": r["quote"], "value": json.loads(r["value"] or "{}"),
            "line_id": r["line_id"], "source_file": r["source_file"],
            "ref": r["ref"], "kind": r["kind"], "surface": r["surface"],
            "link_status": r["status"], "extractor": r["extractor"]}


FACT_SQL = ("SELECT f.*, l.source_file, l.ref, l.kind, m.surface, m.status FROM facts f "
            "JOIN source_lines l USING (line_id) LEFT JOIN mentions m USING (mention_id) ")


def child_detail(conn, child_id: str) -> dict | None:
    c = conn.execute("SELECT c.*, s.state, s.reason, s.evidence, s.rule_refs FROM children c "
                     "JOIN child_states s USING (child_id) WHERE child_id = ?",
                     (child_id,)).fetchone()
    if c is None:
        return None
    evidence = json.loads(c["evidence"])
    orig = _originals(conn)
    facts = [_fact_row(r, orig) for r in conn.execute(
        FACT_SQL + "WHERE f.child_id = ? ORDER BY f.date, l.kind, f.fact_id", (child_id,))]
    by_id = {f["fact_id"]: f for f in facts}
    rules = [dict(r) for r in conn.execute(
        f"SELECT line_id, source_file, ref, text, meta FROM source_lines WHERE line_id IN "
        f"({','.join('?' * len(json.loads(c['rule_refs'])))})", json.loads(c["rule_refs"]))]
    for r in rules:
        r["title"] = json.loads(r.pop("meta"))["title"]
    return {
        "child_id": c["child_id"], "first": c["first"], "class": c["class"],
        "state": c["state"], "reasons": json.loads(c["reason"]),
        "evidence": [by_id[i] for i in evidence if i in by_id],
        "rules": rules,
        "facts": facts,
    }


def source_context(conn, line_id: int, radius: int = 2) -> dict | None:
    """The cited line with its neighbours in the same file, for the citation viewer."""
    line = conn.execute("SELECT * FROM source_lines WHERE line_id = ?", (line_id,)).fetchone()
    if line is None:
        return None
    rows = conn.execute(
        "SELECT * FROM (SELECT * FROM source_lines WHERE source_file = ? AND line_id < ? "
        "ORDER BY line_id DESC LIMIT ?) UNION ALL SELECT * FROM source_lines WHERE line_id = ? "
        "UNION ALL SELECT * FROM (SELECT * FROM source_lines WHERE source_file = ? AND "
        "line_id > ? ORDER BY line_id LIMIT ?) ORDER BY line_id",
        (line["source_file"], line_id, radius, line_id, line["source_file"], line_id,
         radius)).fetchall()
    meta = json.loads(line["meta"])
    texts = _originals(conn)["lines"]
    return {
        "line_id": line_id, "source_file": line["source_file"], "ref": line["ref"],
        "kind": line["kind"], "header": meta.get("header"),
        "lines": [{"line_id": r["line_id"], "ref": r["ref"],
                   "text": texts.get(r["line_id"], r["text"]), "stored_text": r["text"],
                   "meta": json.loads(r["meta"]), "cited": r["line_id"] == line_id}
                  for r in rows],
    }


def review_queue(conn) -> list[dict]:
    names = {r["child_id"]: dict(r) for r in conn.execute(
        "SELECT child_id, first, surname, class FROM children")}
    out = []
    texts = _originals(conn)["lines"]
    for r in conn.execute(
            "SELECT m.mention_id, m.surface, m.candidates, l.line_id, l.source_file, l.ref, "
            "l.text, l.meta FROM mentions m JOIN source_lines l USING (line_id) "
            "WHERE m.status = 'review' ORDER BY l.line_id"):
        scored = json.loads(r["candidates"])
        top = scored[0][1] if scored else 0
        # Only plausible matches: close to the best score and above the review floor.
        cands = [{**names[cid], "child_id": cid} for cid, sc in scored
                 if cid in names and sc >= max(REVIEW_MIN, top - 10)]
        out.append({"mention_id": r["mention_id"], "surface": r["surface"],
                    "line_id": r["line_id"], "source_file": r["source_file"], "ref": r["ref"],
                    "text": texts.get(r["line_id"], r["text"]), "meta": json.loads(r["meta"]),
                    "candidates": cands})
    return out


def resolve_mention(conn, mention_id: int, child_id: str) -> None:
    """Coordinator decision: this mention is this child. Survives pipeline re-runs."""
    m = conn.execute("SELECT m.surface, l.source_file, l.ref FROM mentions m "
                     "JOIN source_lines l USING (line_id) WHERE mention_id = ?",
                     (mention_id,)).fetchone()
    conn.execute("INSERT OR REPLACE INTO link_overrides (source_file, ref, surface, child_id) "
                 "VALUES (?,?,?,?)", (m["source_file"], m["ref"], m["surface"], child_id))
    conn.execute("UPDATE mentions SET status = 'override', child_id = ? WHERE mention_id = ?",
                 (child_id, mention_id))
    conn.execute("UPDATE facts SET child_id = ? WHERE mention_id = ?", (child_id, mention_id))
    _rewrite(conn, mention_id, lambda t: private.pseudonymise(t, [(m["surface"], child_id)]))
    conn.commit()


def _rewrite(conn, mention_id: int, fn) -> None:
    """Apply fn to the stored text of a mention's line and to that line's facts."""
    line_id = conn.execute("SELECT line_id FROM mentions WHERE mention_id = ?",
                           (mention_id,)).fetchone()[0]
    text = conn.execute("SELECT text FROM source_lines WHERE line_id = ?", (line_id,)).fetchone()[0]
    conn.execute("UPDATE source_lines SET text = ? WHERE line_id = ?", (fn(text), line_id))
    for fid, q, sm in conn.execute("SELECT fact_id, quote, summary FROM facts WHERE line_id = ?",
                                   (line_id,)).fetchall():
        conn.execute("UPDATE facts SET quote = ?, summary = ? WHERE fact_id = ?",
                     (fn(q), fn(sm), fid))


def unlinked_facts(conn, mention_id: int) -> list[dict]:
    orig = _originals(conn)
    return [_fact_row(r, orig) for r in conn.execute(FACT_SQL + "WHERE f.mention_id = ?",
                                                     (mention_id,))]


def resolved_mentions(conn) -> list[dict]:
    """Coordinator decisions made in the review queue, newest first."""
    return [dict(r) for r in conn.execute(
        "SELECT m.mention_id, m.surface, m.child_id, c.first, c.surname, c.class, "
        "l.line_id, l.source_file, l.ref, l.text FROM mentions m "
        "JOIN source_lines l USING (line_id) JOIN children c ON c.child_id = m.child_id "
        "WHERE m.status = 'override' ORDER BY m.mention_id DESC")]


def undo_resolution(conn, mention_id: int) -> None:
    """Send a resolved mention back to the review queue."""
    m = conn.execute("SELECT m.surface, m.child_id, l.source_file, l.ref FROM mentions m "
                     "JOIN source_lines l USING (line_id) WHERE mention_id = ?",
                     (mention_id,)).fetchone()
    _rewrite(conn, mention_id,
             lambda t: t.replace(private.token(m["child_id"]), m["surface"], 1))
    conn.execute("DELETE FROM link_overrides WHERE source_file = ? AND ref = ? AND surface = ?",
                 (m["source_file"], m["ref"], m["surface"]))
    conn.execute("UPDATE mentions SET status = 'review', child_id = NULL WHERE mention_id = ?",
                 (mention_id,))
    conn.execute("UPDATE facts SET child_id = NULL WHERE mention_id = ?", (mention_id,))
    conn.commit()
