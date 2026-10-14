"""04 Ask: map a typed question to one of a fixed set of checks over the evidence store.

The local model only chooses which check to run (and reads a number or a name out of the
question). Every answer is computed from the store and carries citations; the model never
writes the answer itself. If the model is unavailable, a keyword fallback is used.
"""

import json
import re
from dataclasses import dataclass, field

from ti.link import Matcher
from ti.state import ATTENTION, CONFLICT, GAP, ON_TRACK

INTENTS = {
    "needs_attention": "children who need coaching attention",
    "conflicts": "children whose records disagree (coach form vs attendance sheet)",
    "not_enough_info": "children without enough records to judge",
    "on_track": "children who are on track",
    "everyone": "all children in the school",
    "missed_sessions": "children who missed more than N sessions (needs n)",
    "fitness_decline": "children whose fitness test times got slower since baseline",
    "concerns": "children with a concern, injury, pain, hurt or tiredness reported by coach or teacher",
    "child": "one named child (needs name)",
}

SUGGESTED = [
    "Who needs attention in School A?",
    "Which children missed more than 3 sessions?",
    "Show conflicts between coach forms and school sheets",
    "Whose fitness got slower since baseline?",
]

SYSTEM = ("You route a school programme coordinator's question to exactly one check. "
          "Reply only with JSON: {\"intent\": one of " + json.dumps(list(INTENTS)) +
          ", \"n\": integer or null, \"name\": string or null}.\n" +
          "\n".join(f"- {k}: {v}" for k, v in INTENTS.items()))


@dataclass
class Answer:
    question: str
    intent: str
    title: str
    note: str
    child_ids: list[str] = field(default_factory=list)
    go_to_child: str | None = None
    routed_by: str = "model"


def _keywords(q: str) -> dict:
    ql = q.lower()
    n = re.search(r"\d+", ql)
    for intent, words in [("conflicts", ["conflict", "disagree"]),
                          ("missed_sessions", ["missed", "absent", "miss "]),
                          ("not_enough_info", ["not enough", "missing", "information"]),
                          ("fitness_decline", ["fitness", "slower", "assessment", "pt "]),
                          ("concerns", ["concern", "injur", "pain"]),
                          ("on_track", ["on track", "doing well"]),
                          ("needs_attention", ["attention", "flag", "help"])]:
        if any(w in ql for w in words):
            return {"intent": intent, "n": int(n.group()) if n else None, "name": None}
    return {"intent": "child", "n": None, "name": q.strip()}


def route(question: str, client) -> tuple[dict, str]:
    try:
        out = client.generate_json(f"Question: {question}", SYSTEM)
        if out.get("intent") in INTENTS:
            return out, "model"
    except Exception:  # model down or bad output: fall back, never fail the screen
        pass
    return _keywords(question), "keywords"


def answer(conn, question: str, client) -> Answer:
    plan, by = route(question, client)
    intent = plan["intent"]
    states = dict(conn.execute("SELECT child_id, state FROM child_states"))
    total = len(states)
    base = f"{total} children checked against the programme guideline. No child is ranked or scored."
    by_state = {"needs_attention": ATTENTION, "conflicts": CONFLICT,
                "not_enough_info": GAP, "on_track": ON_TRACK}
    if intent in by_state:
        ids = [c for c, s in states.items() if s == by_state[intent]]
        return Answer(question, intent, by_state[intent], base, ids, routed_by=by)
    if intent == "everyone":
        return Answer(question, intent, "All children", base, list(states), routed_by=by)
    if intent == "missed_sessions":
        n = int(plan.get("n") or 3)
        rows = conn.execute(
            "SELECT child_id, SUM(json_extract(value, '$.mark') = 'A') FROM facts "
            "WHERE type = 'attendance' AND child_id IS NOT NULL GROUP BY child_id").fetchall()
        ids = [c for c, a in rows if (a or 0) > n]
        return Answer(question, intent, f"Missed more than {n} sessions",
                      f"Counted from the attendance sheets. {base}", ids, routed_by=by)
    if intent == "fitness_decline":
        ids = []
        for (cid,) in conn.execute("SELECT child_id FROM children"):
            r = {}
            for (v,) in conn.execute("SELECT value FROM facts WHERE child_id = ? AND "
                                     "type = 'assessment'", (cid,)):
                v = json.loads(v)
                if not v.get("missing"):
                    r[v["round"]] = v
            if "baseline" in r and "midline" in r and any(
                    r["midline"][k] > r["baseline"][k] for k in ("sprint_50m_s", "run_600m_s")):
                ids.append(cid)
        return Answer(question, intent, "Slower since baseline",
                      f"50m sprint or 600m run time slower at midline. {base}", ids, routed_by=by)
    if intent == "concerns":
        ids = [r[0] for r in conn.execute(
            "SELECT DISTINCT child_id FROM facts WHERE type IN ('concern', 'injury') "
            "AND child_id IS NOT NULL")]
        return Answer(question, intent, "Concerns raised",
                      f"From coach forms and the WhatsApp group. {base}", ids, routed_by=by)
    # a named child
    roster = [dict(r) for r in conn.execute("SELECT child_id, first, surname FROM children")]
    name = (plan.get("name") or question).strip()
    m = Matcher(roster).match(name)
    if m.status == "linked":
        return Answer(question, "child", "", "", [m.child_id], go_to_child=m.child_id,
                      routed_by=by)
    ids = [cid for cid, _ in m.candidates if _ >= 75]
    return Answer(question, "child", "Children matching that name",
                  "More than one child could match. Pick one." if ids else
                  "No child matches that question. Try one of the suggestions.", ids,
                  routed_by=by)
