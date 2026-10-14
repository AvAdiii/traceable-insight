"""Latent truth per child. Planted conditions are designed in, not discovered after the fact."""

import datetime as dt
import random
from dataclasses import dataclass, field

from ti.generator.roster import Child

START = dt.date(2026, 7, 7)  # Tuesday of programme week 1
N_WEEKS = 6

PLAN = (
    ["conflict"] * 4
    + ["gap"] * 4
    + ["needs_attention"] * 5
    + ["on_track"] * 12
)
# Sub-kinds make sure each planted child trips exactly the rule we intend.
GAP_KINDS = ["missing_weeks", "missing_weeks", "no_midline", "no_midline"]
NA_KINDS = ["low_attendance", "low_attendance", "fitness_decline", "fitness_decline", "concerns"]


def sessions() -> list[dt.date]:
    """Two sessions a week (Tue, Fri) for six weeks."""
    out = []
    for w in range(N_WEEKS):
        tue = START + dt.timedelta(weeks=w)
        out += [tue, tue + dt.timedelta(days=3)]
    return out


@dataclass
class Profile:
    condition: str                       # on_track | needs_attention | gap | conflict
    kind: str = ""                       # sub-kind for gap / needs_attention
    present: dict = field(default_factory=dict)   # date -> True/False/None (None = not recorded)
    conflict_date: dt.date | None = None
    baseline: dict = field(default_factory=dict)
    midline: dict | None = None
    concern_budget: int = 0              # how many concern mentions to plant


def _fitness(rng: random.Random) -> dict:
    return {
        "sprint_50m_s": round(rng.uniform(8.6, 10.4), 1),
        "broad_jump_cm": rng.randint(130, 178),
        "run_600m_s": rng.randint(150, 205),
    }


def _midline(base: dict, change: float, rng: random.Random) -> dict:
    """change > 0 means slower/shorter (worse). Times scale up, jump scales down."""
    j = lambda: rng.uniform(-0.01, 0.01)
    return {
        "sprint_50m_s": round(base["sprint_50m_s"] * (1 + change + j()), 1),
        "broad_jump_cm": round(base["broad_jump_cm"] * (1 - change + j())),
        "run_600m_s": round(base["run_600m_s"] * (1 + change + j())),
    }


def _attendance(dates, n_absent, rng, must_absent=None):
    absent = set(rng.sample([d for d in dates if d != must_absent], n_absent - bool(must_absent)))
    if must_absent:
        absent.add(must_absent)
    return {d: d not in absent for d in dates}


def assign_profiles(roster: list[Child], rng: random.Random) -> dict[str, Profile]:
    ids = [c.child_id for c in roster]
    by_name = {c.full: c.child_id for c in roster}
    plan = PLAN[:]
    rng.shuffle(plan)
    cond = dict(zip(ids, plan))
    # Demo guarantees: Ravi Kumar needs attention (variant demo), Ravi Shankar is on track.
    ravis = {by_name["Ravi Kumar"], by_name["Ravi Shankar"]}
    for name, want in [("Ravi Kumar", "needs_attention"), ("Ravi Shankar", "on_track")]:
        cid = by_name[name]
        if cond[cid] != want:
            swap = next(i for i in ids if cond[i] == want and i not in ravis)
            cond[cid], cond[swap] = cond[swap], cond[cid]

    gap_kinds, na_kinds = GAP_KINDS[:], NA_KINDS[:]
    rng.shuffle(gap_kinds)
    rng.shuffle(na_kinds)
    if "low_attendance" in na_kinds:  # Ravi Kumar: low attendance makes the clearest demo
        rk = by_name["Ravi Kumar"]
        order = [i for i in ids if cond[i] == "needs_attention"]
        k = order.index(rk)
        j = na_kinds.index("low_attendance")
        na_kinds[k], na_kinds[j] = na_kinds[j], na_kinds[k]

    dates = sessions()
    out: dict[str, Profile] = {}
    for cid in ids:
        c = cond[cid]
        p = Profile(condition=c)
        p.baseline = _fitness(rng)
        improve = -rng.uniform(0.01, 0.05)
        if c == "on_track":
            p.present = _attendance(dates, rng.randint(0, 2), rng)
            p.midline = _midline(p.baseline, improve, rng)
            p.concern_budget = rng.choice([0, 0, 1])
        elif c == "conflict":
            cd = rng.choice(dates[2:])
            p.conflict_date = cd
            p.present = _attendance(dates, rng.randint(1, 2), rng, must_absent=cd)
            p.midline = _midline(p.baseline, improve, rng)
        elif c == "gap":
            p.kind = gap_kinds.pop()
            p.present = _attendance(dates, rng.randint(0, 2), rng)
            p.midline = _midline(p.baseline, improve, rng)
            if p.kind == "missing_weeks":
                keep = set(dates[:4])  # only weeks 1-2 recorded: 4 of 12 sessions
                p.present = {d: (v if d in keep else None) for d, v in p.present.items()}
            else:
                p.midline = None
        else:
            p.kind = na_kinds.pop(0)
            if p.kind == "low_attendance":
                p.present = _attendance(dates, rng.randint(6, 7), rng)
                p.midline = _midline(p.baseline, improve, rng)
            elif p.kind == "fitness_decline":
                p.present = _attendance(dates, rng.randint(0, 2), rng)
                p.midline = _midline(p.baseline, rng.uniform(0.11, 0.15), rng)
            else:
                p.present = _attendance(dates, rng.randint(0, 2), rng)
                p.midline = _midline(p.baseline, improve, rng)
                p.concern_budget = 3
        out[cid] = p
    return out
