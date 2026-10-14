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


# ---------------------------------------------------------------- Figma screens (Hack 1)

STATE_ORDER = STATES


def display_names(conn) -> dict[str, str]:
    """First name and surname initial, as the coordinator view shows children ("Ravi K.")."""
    return {r["child_id"]: f"{r['first']} {r['surname'][0]}."
            for r in conn.execute("SELECT child_id, first, surname FROM children")}


def home_summary(conn) -> dict:
    """01 Home: one line per school with counts the coordinator acts on."""
    counts = dict(conn.execute("SELECT state, COUNT(*) FROM child_states GROUP BY state"))
    review = conn.execute("SELECT COUNT(*) FROM mentions WHERE status = 'review'").fetchone()[0]
    checks = len(name_checks(conn)["uncertain"])
    actions = conn.execute("SELECT COUNT(DISTINCT child_id) FROM decisions").fetchone()[0]
    last = conn.execute("SELECT MAX(date) FROM facts WHERE type = 'attendance'").fetchone()[0]
    return {"meta": _meta(conn), "counts": counts, "names_to_check": review + checks,
            "actions_saved": actions, "last_session": last,
            "children": sum(counts.values())}


SOURCE_GROUPS = [
    ("whatsapp", "WhatsApp chat", "whatsapp.txt"),
    ("attendance", "Attendance sheets", "attendance_wk*.csv"),
    ("coach_form", "Coach session forms", "coach_forms.csv"),
    ("assessment", "Fitness assessments", "assessments.csv"),
]


def sources_status(conn, school_dir) -> list[dict]:
    """02 Add Sources: what was read from each source, and what was hard to read."""
    meta = _meta(conn)
    rejected = meta.get("rejected_by_file", {})
    out = []
    for kind, label, pattern in SOURCE_GROUPS:
        files = sorted(school_dir.glob(pattern))
        n_lines = conn.execute("SELECT COUNT(*) FROM source_lines WHERE kind = ?",
                               (kind,)).fetchone()[0]
        kids = conn.execute(
            "SELECT COUNT(DISTINCT m.child_id) FROM mentions m JOIN source_lines l "
            "USING (line_id) WHERE l.kind = ? AND m.child_id IS NOT NULL", (kind,)).fetchone()[0]
        detail = {
            "whatsapp": f"{n_lines} messages read",
            "attendance": f"{len(files)} weekly sheets, {n_lines} rows, {kids} children",
            "coach_form": f"{n_lines} session forms read",
            "assessment": f"{n_lines} records, {kids} children",
        }[kind]
        hard = sum(v for f, v in rejected.items() if any(f == x.name for x in files))
        out.append({"kind": kind, "label": label, "files": [f.name for f in files],
                    "detail": detail, "ok": bool(files) and n_lines > 0,
                    "warning": (f"{hard} note{'s' if hard != 1 else ''} could not be traced to "
                                f"the text, so they were left out") if hard else ""})
    return out


def name_checks(conn) -> dict:
    """03 Check Names.

    same_child: per child, the different ways their name was written and linked, with the
      weakest (fuzzy) ones marked uncertain so the coordinator can say Yes or No.
    uncertain: mention groups that need a Yes/No.
    pick: review-queue items where two or more children fit ("Is 'ravi' from ...").
    """
    kids = {r["child_id"]: dict(r) for r in conn.execute("SELECT * FROM children")}
    rows = conn.execute(
        "SELECT m.mention_id, m.surface, m.status, m.child_id, m.score, l.kind, l.source_file, "
        "l.ref, l.line_id FROM mentions m JOIN source_lines l USING (line_id) "
        "WHERE m.child_id IS NOT NULL").fetchall()
    groups: dict[tuple, dict] = {}
    for r in rows:
        c = kids[r["child_id"]]
        if r["surface"] in (c["first"], f"{c['first']} {c['surname']}"):
            continue  # written exactly as on the roster: nothing to check
        g = groups.setdefault((r["child_id"], r["surface"]), {
            "child_id": r["child_id"], "surface": r["surface"], "mention_ids": [],
            "score": r["score"], "kinds": set(), "status": r["status"], "line_id": r["line_id"]})
        g["mention_ids"].append(r["mention_id"])
        g["kinds"].add(r["kind"])
        g["score"] = min(g["score"] or 100, r["score"] or 100)
        if r["status"] == "override":
            g["status"] = "override"
    by_child: dict[str, list] = {}
    for g in groups.values():
        g["kinds"] = sorted(g["kinds"])
        g["uncertain"] = g["status"] != "override" and (g["score"] or 100) < UNCERTAIN_BELOW
        by_child.setdefault(g["child_id"], []).append(g)
    same_child = []
    for cid, gs in by_child.items():
        gs.sort(key=lambda g: (not g["uncertain"], -len(g["mention_ids"])))
        same_child.append({**kids[cid], "variants": gs})
    same_child.sort(key=lambda c: (-sum(v["uncertain"] for v in c["variants"]),
                                   -len(c["variants"]), c["first"]))
    return {"same_child": same_child,
            "uncertain": [g for gs in by_child.values() for g in gs if g["uncertain"]],
            "pick": review_queue(conn)}


UNCERTAIN_BELOW = 95.0   # linked, but by a fuzzy match the coordinator should confirm


def confirm_link(conn, mention_ids: list[int]) -> None:
    """'Yes, same child': keep the link and remember the decision across re-runs."""
    for mid in mention_ids:
        m = conn.execute("SELECT m.surface, m.child_id, l.source_file, l.ref FROM mentions m "
                         "JOIN source_lines l USING (line_id) WHERE mention_id = ?",
                         (mid,)).fetchone()
        conn.execute("INSERT OR REPLACE INTO link_overrides (source_file, ref, surface, child_id) "
                     "VALUES (?,?,?,?)", (m["source_file"], m["ref"], m["surface"], m["child_id"]))
        conn.execute("UPDATE mentions SET status = 'override' WHERE mention_id = ?", (mid,))
    conn.commit()


def reject_link(conn, mention_ids: list[int]) -> None:
    """'No': this name is not that child. The facts leave the child and the text gets the
    written name back."""
    for mid in mention_ids:
        m = conn.execute("SELECT m.surface, m.child_id, l.source_file, l.ref FROM mentions m "
                         "JOIN source_lines l USING (line_id) WHERE mention_id = ?",
                         (mid,)).fetchone()
        _rewrite(conn, mid, lambda t, m=m: t.replace(private.token(m["child_id"]),
                                                     m["surface"], 1))
        conn.execute("INSERT OR REPLACE INTO link_overrides (source_file, ref, surface, child_id) "
                     "VALUES (?,?,?,'-')", (m["source_file"], m["ref"], m["surface"]))
        conn.execute("UPDATE mentions SET status = 'unlinked', child_id = NULL "
                     "WHERE mention_id = ?", (mid,))
        conn.execute("UPDATE facts SET child_id = NULL WHERE mention_id = ?", (mid,))
    conn.commit()


def link_stats(conn, child_id: str) -> dict:
    """'Linked from 5 mentions across 3 sources. Lowest name match 88%.'"""
    r = conn.execute(
        "SELECT COUNT(*), COUNT(DISTINCT l.kind), MIN(m.score) FROM mentions m "
        "JOIN source_lines l USING (line_id) WHERE m.child_id = ?", (child_id,)).fetchone()
    return {"mentions": r[0], "sources": r[1], "lowest": r[2]}


def save_resolution(conn, child_id: str, date: str, choice: str, sources: list[int]) -> None:
    conn.execute("INSERT OR REPLACE INTO resolutions (child_id, date, choice, sources) "
                 "VALUES (?,?,?,?)", (child_id, date, choice, json.dumps(sources)))
    conn.commit()


def resolutions(conn, child_id: str) -> list[dict]:
    return [dict(r) for r in conn.execute(
        "SELECT * FROM resolutions WHERE child_id = ? ORDER BY date", (child_id,))]


def clear_resolution(conn, child_id: str, date: str) -> None:
    conn.execute("DELETE FROM resolutions WHERE child_id = ? AND date = ?", (child_id, date))
    conn.commit()


def save_decision(conn, child_id: str, action: str, coach: str, start: str | None,
                  end: str | None, notes: str, sources: list[int]) -> int:
    state = conn.execute("SELECT state FROM child_states WHERE child_id = ?",
                         (child_id,)).fetchone()
    cur = conn.execute(
        "INSERT INTO decisions (child_id, action, coach, start_date, end_date, notes, sources, "
        "state_at_decision) VALUES (?,?,?,?,?,?,?,?)",
        (child_id, action.strip(), coach.strip(), start, end, notes.strip(),
         json.dumps(sources), state[0] if state else None))
    conn.commit()
    return cur.lastrowid


def decisions(conn, child_id: str | None = None) -> list[dict]:
    names = display_names(conn)
    cls = dict(conn.execute("SELECT child_id, class FROM children"))
    sql = "SELECT * FROM decisions"
    args: tuple = ()
    if child_id:
        sql += " WHERE child_id = ?"
        args = (child_id,)
    out = []
    for r in conn.execute(sql + " ORDER BY decision_id DESC", args):
        d = dict(r)
        d["sources"] = json.loads(d["sources"])
        d["name"] = names.get(d["child_id"], d["child_id"])
        d["class"] = cls.get(d["child_id"], "")
        out.append(d)
    return out


def results(conn, child_ids: list[str] | None = None) -> dict:
    """05 Results: children grouped by state (optionally a subset), each with its reasons
    and how many cited facts back them."""
    names = display_names(conn)
    groups = {s: [] for s in STATES}
    q = ("SELECT c.child_id, c.class, s.state, s.reason, s.evidence FROM children c "
         "JOIN child_states s USING (child_id) ORDER BY c.first")
    for r in conn.execute(q):
        if child_ids is not None and r["child_id"] not in child_ids:
            continue
        groups[r["state"]].append({
            "child_id": r["child_id"], "name": names[r["child_id"]], "class": r["class"],
            "reasons": json.loads(r["reason"]), "n_evidence": len(json.loads(r["evidence"]))})
    return groups
