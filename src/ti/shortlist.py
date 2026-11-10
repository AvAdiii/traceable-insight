"""Suggest athletes for a meet item from the latest test battery, with cited reasons.

Each discipline leans on the tests that predict it (editable weights). A child's score is the
weighted mean of their percentiles among children of the same gender and age. Values waiting for a
data check never count; strong children held back by one are listed so nobody is dropped silently.
"""

import datetime as dt
from collections import defaultdict

from sqlalchemy import select

from ti.db import Child, ChildRound, EventItem, Event, Measurement, Record, Round, School, Selection, Upload
from ti.pipeline import VALID
from ti.template import TESTS

DISCIPLINES = {
    "sprint": {"label": "Sprint", "examples": "50 m · 60 m · 100 m", "weights": {"shuttle": 0.7, "jump": 0.3}},
    "long_jump": {"label": "Jumps", "examples": "long jump · broad jump · high jump", "weights": {"jump": 0.8, "shuttle": 0.2}},
    "throw": {"label": "Throws", "examples": "shot put · ball throw", "weights": {"ball": 0.85, "jump": 0.15}},
    "endurance": {"label": "Middle distance", "examples": "400 m · 600 m · 800 m", "weights": {"relay": 0.75, "shuttle": 0.25}},
    "relay": {"label": "Relay", "examples": "4×100 m · 4×400 m", "weights": {"shuttle": 0.6, "relay": 0.4}},
    "all_round": {"label": "All-round", "examples": "champion of champions",
                  "weights": {"jump": 0.25, "ball": 0.25, "shuttle": 0.25, "relay": 0.25}},
}


def age_at(kid: Child, cr: ChildRound, rnd: Round, on: dt.date) -> float | None:
    if kid.dob:
        return (on - kid.dob).days / 365.25
    if cr.age is not None:
        return cr.age + (on - rnd.test_date).days / 365.25
    return None


def cite(s, m: Measurement) -> dict:
    r = s.get(Record, m.record_id)
    u = s.get(Upload, r.upload_id)
    return {"measurement_id": m.id, "record_id": r.id, "file": u.filename, "sheet": r.sheet,
            "cell": m.cell, "raw": m.raw}


def fmt(f: str, v: float) -> str:
    return f"{v:.2f} {TESTS[f].unit}" if f != "shuttle" and f != "relay" else f"{v:.1f} {TESTS[f].unit}"


def latest_rounds(s, school_ids=None) -> dict[str, tuple[ChildRound, Round]]:
    rounds = {r.id: r for r in s.scalars(select(Round))}
    q = select(ChildRound)
    if school_ids is not None:
        q = q.where(ChildRound.school_id.in_(school_ids))
    out = {}
    for cr in s.scalars(q):
        r = rounds[cr.round_id]
        if cr.child_id not in out or r.test_date > out[cr.child_id][1].test_date:
            out[cr.child_id] = (cr, r)
    return out


def rank(s, weights: dict, *, gender="Any", age_min=None, age_max=None, on: dt.date | None = None,
         school_ids=None, exclude: set | None = None) -> tuple[list, list, int]:
    """-> (ranked candidates, held back by data checks, pool size)."""
    on = on or dt.date.today()
    latest = latest_rounds(s, school_ids)
    kids = {c.id: c for c in s.scalars(select(Child).where(Child.id.in_(latest)))}
    schools = {x.id: x for x in s.scalars(select(School))}
    ms = defaultdict(dict)
    pairs = {(cid, cr.round_id) for cid, (cr, _) in latest.items()}
    for m in s.scalars(select(Measurement).where(Measurement.child_id.in_(latest),
                                                 Measurement.field.in_(list(weights)))):
        if (m.child_id, m.round_id) in pairs:
            ms[m.child_id][m.field] = m
    prev = _previous_composites(s, latest)
    main = max(weights, key=weights.get)
    out, held, pool = [], [], 0
    for cid, (cr, rnd) in latest.items():
        kid = kids[cid]
        if exclude and cid in exclude:
            continue
        if gender in ("Boys", "Girls") and kid.gender != gender:
            continue
        age = age_at(kid, cr, rnd, on)
        if age_min is not None and (age is None or int(age) < age_min):
            continue
        if age_max is not None and (age is None or int(age) > age_max):
            continue
        pool += 1
        fs = ms.get(cid, {})
        valid = {f: m for f, m in fs.items() if m.status in VALID and m.percentile is not None}
        blocked = [f for f, m in fs.items() if m.status in ("suspect", "disputed")]
        base = {"child_id": cid, "name": kid.name, "gender": kid.gender, "klass": cr.klass,
                "school_id": cr.school_id, "school": schools[cr.school_id].short,
                "age": round(age, 1) if age else None, "round": rnd.label}
        if main not in valid:
            if main in blocked:
                held.append({**base, "why": f"{TESTS[main].label} waiting for a data check",
                             "issue_field": main})
            continue
        tot = sum(weights[f] for f in valid)
        score = sum(valid[f].percentile * weights[f] for f in valid) / tot
        reasons = [{"field": f, "label": TESTS[f].label, "value": valid[f].value,
                    "text": fmt(f, valid[f].value), "percentile": valid[f].percentile,
                    "pool": valid[f].pool, "weight": weights[f], "cite": cite(s, valid[f])}
                   for f in sorted(valid, key=lambda f: -weights[f])]
        trend = None
        if cid in prev and cr.composite is not None:
            trend = round(cr.composite - prev[cid], 1)
        summary = " · ".join(f"{r['label']} {r['text']} (P{r['percentile']:.0f})" for r in reasons[:2])
        out.append({**base, "score": round(score, 1), "reasons": reasons, "trend": trend,
                    "missing": [f for f in weights if f not in valid], "summary": summary,
                    "composite": cr.composite})
    out.sort(key=lambda x: (-x["score"], -(x["composite"] or 0)))
    return out, held, pool


def _previous_composites(s, latest) -> dict[str, float]:
    rounds = {r.id: r for r in s.scalars(select(Round))}
    best: dict[str, tuple] = {}
    for cr in s.scalars(select(ChildRound).where(ChildRound.child_id.in_(latest))):
        last_cr, last_r = latest[cr.child_id]
        r = rounds[cr.round_id]
        if r.test_date < last_r.test_date and cr.composite is not None:
            if cr.child_id not in best or r.test_date > best[cr.child_id][0]:
                best[cr.child_id] = (r.test_date, cr.composite)
    return {k: v[1] for k, v in best.items()}


def suggest(s, item: EventItem, allowed=None) -> dict:
    ev = s.get(Event, item.event_id)
    weights = DISCIPLINES[item.discipline]["weights"]
    school_ids = set(ev.school_ids) if ev.school_ids else None
    if allowed is not None:
        school_ids = (school_ids & allowed) if school_ids else allowed
    others = defaultdict(list)
    for sel, it in s.execute(select(Selection, EventItem).join(EventItem).where(
            EventItem.event_id == ev.id, EventItem.id != item.id)):
        others[sel.child_id].append(f"{it.name} ({it.gender})")
    ranked, held, pool = rank(s, weights, gender=item.gender, age_min=item.age_min,
                              age_max=item.age_max, on=ev.start_date, school_ids=school_ids)
    for c in ranked:
        if c["child_id"] in others:
            c["also"] = others[c["child_id"]]
    n, r = item.slots, item.reserves
    top = ranked[: n + r + 10]
    best_score = top[0]["score"] if top else 0
    held = [h for h in held][:8]
    return {"selected": top[:n], "reserves": top[n:n + r], "more": top[n + r:],
            "held": held, "pool": pool, "weights": weights,
            "discipline": DISCIPLINES[item.discipline], "best_score": best_score}
