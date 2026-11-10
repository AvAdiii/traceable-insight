"""Score the store against the generator's ground truth: `uv run python -m ti.verify`."""

import json
from collections import Counter, defaultdict

from sqlalchemy import select

from ti import config, db
from ti.db import Issue, Record, Upload


def report(verbose: bool = True) -> dict:
    truth = json.loads((config.DEMO_DIR / "ground_truth.json").read_text())
    s = db.session()
    ups = {u.id: u.filename for u in s.scalars(select(Upload))}
    tid_of = {(f, r["row"]): r["tid"] for f, rows in truth["rows"].items() for r in rows}
    by_tid, by_child = defaultdict(set), defaultdict(set)
    unlinked = review = 0
    wrong = []
    for r in s.scalars(select(Record).where(Record.preferred)):
        tid = tid_of.get((ups[r.upload_id], r.row))
        if tid is None:
            continue
        if r.child_id is None:
            review += r.link_status == "review"
            unlinked += 1
            continue
        by_tid[tid].add(r.child_id)
        by_child[r.child_id].add(tid)
    split = {t: c for t, c in by_tid.items() if len(c) > 1}
    merged = {c: t for c, t in by_child.items() if len(t) > 1}
    issues = Counter(i.kind for i in s.scalars(select(Issue)))
    out = {"children_true": truth["children"], "children_found": len(by_child),
           "split_children": len(split), "merged_children": len(merged),
           "rows_waiting_review": review, "issues": dict(issues)}
    if verbose:
        print(json.dumps(out, indent=1))
        recs = {}
        for c, ts in list(merged.items())[:5]:
            print("merged", c, ts)
        for t, cs in list(split.items())[:8]:
            names = [(r.name, r.parent, str(r.dob), ups[r.upload_id][14:22]) for r in s.scalars(select(Record).where(Record.child_id.in_(cs), Record.preferred))]
            print("split", t, sorted(set(names)))
    return out


if __name__ == "__main__":  # pragma: no cover
    report()
