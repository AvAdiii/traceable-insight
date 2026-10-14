"""#15 Score a pipeline run against ground_truth.json. Only this module reads the truth file.

`uv run python -m ti.score --school school_a`
"""

import argparse
import json
import sys

from ti import config
from ti.state import CONFLICT, GAP
from ti.store import db

TARGETS = {"link_accuracy": 0.85, "conflicts_recovered": 3, "gaps_recovered": 3,
           "citations_resolve": 1.0}


def compute(school: str, db_path=None, data_dir=None) -> dict:
    truth = json.loads(((data_dir or config.DATA_DIR) / school / "ground_truth.json").read_text())
    conn = db.connect(db_path or config.db_path(school))

    found = {}
    for r in conn.execute("SELECT l.source_file, l.ref, m.surface, m.status, m.child_id "
                          "FROM mentions m JOIN source_lines l USING (line_id)"):
        found[(r[0], r[1], r[2])] = (r[3], r[4])
    correct, misses = 0, []
    for m in truth["mentions"]:
        status, child = found.get((m["file"], m["ref"], m["surface"]), ("missing", None))
        if m["child_id"] == "ambiguous":
            ok = status == "review"
        else:
            ok = status in ("linked", "override") and child == m["child_id"]
        correct += ok
        if not ok:
            misses.append({**m, "got_status": status, "got_child": child})

    states = {r[0]: r[1] for r in conn.execute("SELECT child_id, state FROM child_states")}
    conflicts = sum(states.get(c["child_id"]) == CONFLICT for c in truth["planted_conflicts"])
    gaps = sum(states.get(g["child_id"]) == GAP for g in truth["planted_gaps"])
    expected = {c["child_id"]: c["expected_state"] for c in truth["children"]}
    state_hits = sum(states.get(cid) == s for cid, s in expected.items())
    wrong_states = [{"child_id": cid, "expected": s, "got": states.get(cid)}
                    for cid, s in expected.items() if states.get(cid) != s]

    # A citation resolves when the stored (pseudonymised) quote sits in the stored line AND,
    # when the private copy is here, the original quote sits in the original line.
    from ti.store import private
    meta = {k: json.loads(v) for k, v in conn.execute("SELECT key, value FROM run_meta")}
    orig = private.load(meta.get("private_copy"))
    facts = conn.execute("SELECT f.fact_id, f.line_id, f.quote, l.text FROM facts f "
                         "JOIN source_lines l USING (line_id)").fetchall()
    resolving = 0
    for fid, lid, q, t in facts:
        ok = q in t
        if orig["lines"]:
            ok = ok and orig["facts"][fid]["quote"] in orig["lines"][lid]
        resolving += ok

    res = {
        "link_accuracy": round(correct / len(truth["mentions"]), 3),
        "mentions_total": len(truth["mentions"]),
        "conflicts_recovered": conflicts, "conflicts_planted": len(truth["planted_conflicts"]),
        "gaps_recovered": gaps, "gaps_planted": len(truth["planted_gaps"]),
        "states_correct": state_hits, "children": len(expected),
        "citations_resolve": round(resolving / len(facts), 3) if facts else 0.0,
        "facts_total": len(facts),
        "wrong_states": wrong_states,
        "link_misses": misses,
    }
    res["targets"] = {k: res[k] >= v for k, v in TARGETS.items()}
    res["all_targets_met"] = all(res["targets"].values())
    return res


def report(school: str, db_path=None, data_dir=None, out=sys.stdout) -> dict:
    res = compute(school, db_path, data_dir)
    (config.VAR_DIR / "score.json").write_text(json.dumps(res, indent=2))
    tick = lambda ok: "PASS" if ok else "FAIL"
    t = res["targets"]
    print("\nGround-truth check", file=out)
    print(f"  {tick(t['link_accuracy'])}  name links correct  {res['link_accuracy']:.1%} "
          f"of {res['mentions_total']} (target >= 85%)", file=out)
    print(f"  {tick(t['conflicts_recovered'])}  conflicts found     {res['conflicts_recovered']}"
          f"/{res['conflicts_planted']} (target >= 3)", file=out)
    print(f"  {tick(t['gaps_recovered'])}  gaps found          {res['gaps_recovered']}"
          f"/{res['gaps_planted']} (target >= 3)", file=out)
    print(f"  {tick(t['citations_resolve'])}  citations resolve   {res['citations_resolve']:.0%} "
          f"of {res['facts_total']} facts (target 100%)", file=out)
    print(f"        states correct      {res['states_correct']}/{res['children']}", file=out)
    for w in res["wrong_states"]:
        print(f"        - {w['child_id']}: expected {w['expected']}, got {w['got']}", file=out)
    return res


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--school", default="school_a")
    sys.exit(0 if report(ap.parse_args().school)["all_targets_met"] else 1)
