"""A6 state engine: exactly one state per child, by precedence, with its evidence.

Precedence: Conflict to review > Not enough information > Needs attention > On track.
The engine flags and cites; the coordinator decides.
"""

import json
from dataclasses import dataclass, field

CONFLICT = "Conflict to review"
GAP = "Not enough information"
ATTENTION = "Needs attention"
ON_TRACK = "On track"
STATES = [CONFLICT, GAP, ATTENTION, ON_TRACK]

# Guideline sections each rule rests on (looked up by title, cited in the UI).
RULE_SECTIONS = {
    CONFLICT: "Conflicting records",
    GAP: "Enough information to judge",
    "attendance": "Minimum attendance",
    "fitness": "Fitness decline",
    "concerns": "Repeated concerns",
}


@dataclass
class ChildState:
    state: str
    reasons: list[str]
    evidence: list[int] = field(default_factory=list)
    rules: list[str] = field(default_factory=list)
    resolved: list[dict] = field(default_factory=list)   # coordinator decisions on conflicts

    @property
    def reason(self) -> str:
        return " ".join(self.reasons)


def _facts(conn, child_id):
    return conn.execute(
        "SELECT f.*, l.kind AS line_kind FROM facts f JOIN source_lines l USING (line_id) "
        "WHERE f.child_id = ? ORDER BY f.date, f.fact_id", (child_id,)).fetchall()


def _pct(base: float, mid: float) -> float:
    return 100.0 * (mid - base) / base


def _day(iso: str) -> str:
    y, m, d = iso.split("-")
    return f"{int(d)} {'Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec'.split()[int(m) - 1]}"


def evaluate(facts, th: dict, resolutions: dict | None = None) -> ChildState:
    """resolutions: date -> "coach" | "school" | "ask", the coordinator's answer to
    "Which one is right?" for a conflict on that date."""
    resolutions = resolutions or {}
    attendance = {}                      # date -> (mark, fact_id); later rows win
    for f in facts:
        if f["type"] == "attendance":
            attendance[f["date"]] = (json.loads(f["value"])["mark"], f["fact_id"])
    resolved = []
    for date, choice in resolutions.items():
        if choice == "coach" and attendance.get(date, (None,))[0] == "A":
            attendance[date] = ("P", attendance[date][1])   # coach form is right: count it
        if choice in ("coach", "school"):
            resolved.append({"date": date, "choice": choice})
    rounds, missing_rounds = {}, {}
    for f in facts:
        if f["type"] == "assessment":
            v = json.loads(f["value"])
            if v.get("missing"):
                missing_rounds[v["round"]] = f["fact_id"]
            else:
                rounds[v["round"]] = (v, f["fact_id"])
    concerns = [f for f in facts if f["type"] in ("concern", "injury")]

    # 1. Conflict: coach form says the child took part on a day the sheet marks absent.
    conflicts = []
    for f in facts:
        if f["line_kind"] == "coach_form" and f["type"] in ("praise", "participation") \
                and attendance.get(f["date"], (None,))[0] == "A" \
                and resolutions.get(f["date"]) != "school":
            conflicts.append((f, attendance[f["date"]][1]))
    if conflicts:
        reasons = []
        for f, _ in conflicts:
            r = (f"Coach form says they took part on {_day(f['date'])}, but the attendance "
                 f"sheet marks them absent that day.")
            if resolutions.get(f["date"]) == "ask":
                r += " Waiting for the coach to confirm."
            reasons.append(r)
        ev = [i for f, a in conflicts for i in (f["fact_id"], a)]
        return ChildState(CONFLICT, reasons, ev, [RULE_SECTIONS[CONFLICT]])

    # 2. Not enough information to judge.
    recorded = len(attendance)
    gaps = []
    if recorded < th["min_recorded_sessions"]:
        gaps.append(f"Attendance recorded for only {recorded} of {th['sessions_planned']} "
                    f"sessions (needs {th['min_recorded_sessions']}).")
    if th.get("require_midline_assessment") and "midline" not in rounds:
        gaps.append("No midline fitness assessment on record.")
    if gaps:
        ev = [fid for _, fid in attendance.values()] + [fid for _, fid in rounds.values()] \
            + list(missing_rounds.values())
        return ChildState(GAP, gaps, ev, [RULE_SECTIONS[GAP]], resolved)

    # 3. Needs attention.
    reasons, ev, rules = [], [], []
    present = sum(1 for m, _ in attendance.values() if m == "P")
    rate = present / recorded
    if rate < th["attendance_rate_min"]:
        reasons.append(f"Attended {present} of {recorded} recorded sessions "
                       f"({rate:.0%}, below {th['attendance_rate_min']:.0%}).")
        ev += [fid for m, fid in attendance.values() if m == "A"]
        rules.append(RULE_SECTIONS["attendance"])
    if "baseline" in rounds and "midline" in rounds:
        (b, bid), (m, mid) = rounds["baseline"], rounds["midline"]
        slower = {"600m run": _pct(b["run_600m_s"], m["run_600m_s"]),
                  "50m sprint": _pct(b["sprint_50m_s"], m["sprint_50m_s"])}
        worst = max(slower, key=slower.get)
        if slower[worst] > th["fitness_decline_pct"]:
            reasons.append(f"{worst} time is {slower[worst]:.0f}% slower at midline than at "
                           f"baseline (limit {th['fitness_decline_pct']:g}%).")
            ev += [bid, mid]
            rules.append(RULE_SECTIONS["fitness"])
    if len(concerns) >= th["concern_mentions_min"]:
        reasons.append(f"{len(concerns)} concerns raised by coach or teacher.")
        ev += [f["fact_id"] for f in concerns]
        rules.append(RULE_SECTIONS["concerns"])
    if reasons:
        return ChildState(ATTENTION, reasons, ev, rules, resolved)

    # 4. On track.
    msg = [f"Attended {present} of {recorded} recorded sessions."]
    ev = [fid for _, fid in attendance.values()]
    if "midline" in rounds:
        msg.append("Fitness steady or improving since baseline.")
        ev += [fid for _, fid in rounds.values()]
    return ChildState(ON_TRACK, msg, ev, [], resolved)


def assign_states(conn, th: dict) -> dict[str, ChildState]:
    titles = {json.loads(r["meta"])["title"]: r["line_id"] for r in conn.execute(
        "SELECT line_id, meta FROM source_lines WHERE kind = 'guideline'")}
    out = {}
    res: dict[str, dict] = {}
    for r in conn.execute("SELECT child_id, date, choice FROM resolutions"):
        res.setdefault(r[0], {})[r[1]] = r[2]
    conn.execute("DELETE FROM child_states")
    for (cid,) in conn.execute("SELECT child_id FROM children ORDER BY child_id").fetchall():
        st = evaluate(_facts(conn, cid), th, res.get(cid))
        out[cid] = st
        refs = [titles[t] for t in st.rules if t in titles]
        conn.execute("INSERT INTO child_states VALUES (?,?,?,?,?)",
                     (cid, st.state, json.dumps(st.reasons), json.dumps(st.evidence),
                      json.dumps(refs)))
    conn.commit()
    return out
