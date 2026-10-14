"""ingest -> extract -> link -> state for one school, into a fresh SQLite store."""

import datetime as dt
import time

from ti import config
from ti.extract import extract_line
from ti.ingest import load_roster, load_school
from ti.link import Matcher
from ti.state import assign_states
from ti.store import db, private, thresholds


def run(school: str, client, db_path=None, data_dir=None, log=print,
        private_dir=None) -> dict:
    t0 = time.time()
    school_dir = (data_dir or config.DATA_DIR) / school
    conn = db.connect(db_path or config.db_path(school))
    db.init(conn)

    roster = load_roster(school_dir)
    lines = load_school(school_dir)
    db.insert_children(conn, roster)
    line_ids = db.insert_lines(conn, lines)
    log(f"ingest   {len(lines)} source lines from {school_dir.name}")

    matcher = Matcher(roster)
    overrides = db.overrides(conn)
    n_facts = rejected = 0
    status_counts: dict[str, int] = {}
    originals: dict[int, str] = {}
    original_facts: dict[int, dict] = {}
    free_text = [l for l in lines if l.kind in ("whatsapp", "coach_form")]
    done = 0
    for line in lines:
        facts, rej = extract_line(line, client)
        rejected += rej
        if line.kind in ("whatsapp", "coach_form"):
            done += 1
            if done % 25 == 0 or done == len(free_text):
                log(f"extract  {done}/{len(free_text)} free-text lines")
        line_id = line_ids[(line.source_file, line.ref)]
        mention_ids: dict[str, tuple[int, str | None]] = {}
        names = [f.pop("name") for f in facts]
        if "name" in line.meta and line.meta["name"] not in names:
            names.append(line.meta["name"])  # a sheet row names a child even with blank cells
        for name in names:
            if name not in mention_ids:
                key = (line.source_file, line.ref, name)
                r = matcher.match(name)
                if r.status == "skipped":
                    continue
                status, child = (("override", overrides[key]) if key in overrides
                                 else (r.status, r.child_id))
                status_counts[status] = status_counts.get(status, 0) + 1
                mid = db.insert_mention(conn, line_id, name, status, child, r.score, r.candidates)
                mention_ids[name] = (mid, child)
        # Linked names become roster ids in the store; originals go to the private copy.
        pairs = [(n, child) for n, (_, child) in mention_ids.items() if child]
        originals[line_id] = line.text
        if pairs:
            db.update_line_text(conn, line_id, private.pseudonymise(line.text, pairs))
        for name, f in zip(names, facts):
            if name not in mention_ids:
                continue
            mid, child = mention_ids[name]
            stored = {**f, "quote": private.pseudonymise(f["quote"], pairs),
                      "summary": private.pseudonymise(f["summary"], pairs)}
            fid = db.insert_fact(conn, {**stored, "line_id": line_id, "mention_id": mid,
                                        "child_id": child})
            original_facts[fid] = {"quote": f["quote"], "summary": f["summary"]}
            n_facts += 1
    log(f"link     {status_counts}")

    priv = private.path(school, private_dir)
    private.write(priv, originals, original_facts)
    log(f"private  original lines kept at {priv}")

    states = assign_states(conn, thresholds.load(school_dir.parent / "programme" /
                                                 "thresholds.yaml"))
    counts: dict[str, int] = {}
    for s in states.values():
        counts[s.state] = counts.get(s.state, 0) + 1
    summary = {"school": school, "source_lines": len(lines), "facts": n_facts,
               "rejected_facts": rejected, "mentions": status_counts, "states": counts,
               "model": getattr(client, "model", "fake"),
               "private_copy": str(priv),
               "ran_at": dt.datetime.now().isoformat(timespec="seconds"),
               "seconds": round(time.time() - t0, 1)}
    db.set_meta(conn, **summary)
    conn.commit()
    log(f"state    {counts}")
    return summary


def recompute_states(conn, school: str, data_dir=None) -> None:
    """Re-run A6 after the coordinator resolves a review item."""
    th = thresholds.load((data_dir or config.DATA_DIR) / "programme" / "thresholds.yaml")
    assign_states(conn, th)
