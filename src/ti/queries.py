"""Read layer shared by the coordinator view (A8) and the API (A7).

Shows only what the decision needs: first name, class, state and cited facts.
No scores or rankings of children are exposed.
"""

import json

from ti.state import STATES


def _meta(conn) -> dict:
    return {k: json.loads(v) for k, v in conn.execute("SELECT key, value FROM run_meta")}


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


def _fact_row(r) -> dict:
    return {"fact_id": r["fact_id"], "type": r["type"], "date": r["date"], "quote": r["quote"],
            "summary": r["summary"], "line_id": r["line_id"], "source_file": r["source_file"],
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
    facts = [_fact_row(r) for r in conn.execute(
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
    return {
        "line_id": line_id, "source_file": line["source_file"], "ref": line["ref"],
        "kind": line["kind"], "header": meta.get("header"),
        "lines": [{"line_id": r["line_id"], "ref": r["ref"], "text": r["text"],
                   "meta": json.loads(r["meta"]), "cited": r["line_id"] == line_id}
                  for r in rows],
    }


def review_queue(conn) -> list[dict]:
    names = {r["child_id"]: dict(r) for r in conn.execute(
        "SELECT child_id, first, surname, class FROM children")}
    out = []
    for r in conn.execute(
            "SELECT m.mention_id, m.surface, m.candidates, l.line_id, l.source_file, l.ref, "
            "l.text, l.meta FROM mentions m JOIN source_lines l USING (line_id) "
            "WHERE m.status = 'review' ORDER BY l.line_id"):
        cands = [{**names[cid], "child_id": cid} for cid, _ in json.loads(r["candidates"])
                 if cid in names]
        out.append({"mention_id": r["mention_id"], "surface": r["surface"],
                    "line_id": r["line_id"], "source_file": r["source_file"], "ref": r["ref"],
                    "text": r["text"], "meta": json.loads(r["meta"]), "candidates": cands})
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
    conn.commit()


def unlinked_facts(conn, mention_id: int) -> list[dict]:
    return [_fact_row(r) for r in conn.execute(FACT_SQL + "WHERE f.mention_id = ?",
                                               (mention_id,))]
