"""Read layer shared by every API route. Every number it returns carries its cell citation."""

import datetime as dt
from collections import Counter, defaultdict
from statistics import mean, median

from sqlalchemy import select

from ti import shortlist
from ti.db import (Child, ChildRound, Event, EventItem, Flag, Issue, Measurement, Record, Result,
                   Round, School, Selection, Todo, Upload, User)
from ti.pipeline import VALID
from ti.template import ALL, BODY, TESTS

FLAG_META = {
    "top": {"label": "Top performer", "short": "Top"},
    "improved": {"label": "Most improved", "short": "Improved"},
    "push": {"label": "Needs a push", "short": "Needs a push"},
    "declining": {"label": "Declining", "short": "Declining"},
    "missing": {"label": "Missing test", "short": "Missing"},
}


def rounds(s) -> list[Round]:
    return sorted(s.scalars(select(Round)), key=lambda r: r.test_date)


def round_dict(r: Round) -> dict:
    return {"id": r.id, "label": r.label, "kind": r.kind, "test_date": r.test_date.isoformat()}


def _scope(q, col, allowed):
    return q if allowed is None else q.where(col.in_(allowed))


def meta(s, user: User, allowed) -> dict:
    users = {u.id: u for u in s.scalars(select(User))}
    schools = [school_brief(x, users) for x in s.scalars(_scope(select(School), School.id, allowed))]
    return {
        "user": user_dict(user),
        "schools": sorted(schools, key=lambda x: x["short"]),
        "rounds": [round_dict(r) for r in rounds(s)],
        "tests": [{"key": t.key, "label": t.label, "full": t.full, "unit": t.unit, "skill": t.skill,
                   "lower_is_better": t.lower_is_better} for t in TESTS.values()],
        "disciplines": [{"key": k, **{kk: vv for kk, vv in v.items()}}
                        for k, v in shortlist.DISCIPLINES.items()],
        "flags": [{"key": k, **v} for k, v in FLAG_META.items()],
        "coaches": [user_dict(u) for u in users.values() if u.role != "manager"],
    }


def user_dict(u: User | None) -> dict | None:
    if u is None:
        return None
    return {"id": u.id, "name": u.name, "email": u.email, "role": u.role}


def school_brief(x: School, users: dict) -> dict:
    return {"id": x.id, "name": x.name, "short": x.short, "area": x.area, "hue": x.hue,
            "trainer": user_dict(users.get(x.trainer_id)),
            "supervisor": user_dict(users.get(x.supervisor_id))}


# ------------------------------------------------------------------ children

def latest_by_child(s, allowed, round_id=None) -> dict[str, ChildRound]:
    rmap = {r.id: r for r in rounds(s)}
    q = _scope(select(ChildRound), ChildRound.school_id, allowed)
    if round_id:
        q = q.where(ChildRound.round_id == round_id)
    out = {}
    for cr in s.scalars(q):
        if cr.child_id not in out or rmap[cr.round_id].test_date > rmap[out[cr.child_id].round_id].test_date:
            out[cr.child_id] = cr
    return out


def _prev_composite(s, latest: dict[str, ChildRound]) -> dict[str, float]:
    rmap = {r.id: r for r in rounds(s)}
    out = {}
    best = {}
    for cr in s.scalars(select(ChildRound).where(ChildRound.child_id.in_(list(latest)))):
        cur = latest[cr.child_id]
        if rmap[cr.round_id].test_date < rmap[cur.round_id].test_date and cr.composite is not None:
            if cr.child_id not in best or rmap[cr.round_id].test_date > best[cr.child_id]:
                best[cr.child_id] = rmap[cr.round_id].test_date
                out[cr.child_id] = cr.composite
    return out


def children(s, allowed, *, q=None, school=None, klass=None, gender=None, age_min=None,
             age_max=None, flag=None, test=None, sort="best", round_id=None, coach=None,
             limit=60, offset=0) -> dict:
    latest = latest_by_child(s, allowed, round_id)
    kids = {c.id: c for c in s.scalars(select(Child).where(Child.id.in_(list(latest))))}
    schools = {x.id: x for x in s.scalars(select(School))}
    flags = defaultdict(list)
    for f in s.scalars(select(Flag).where(Flag.child_id.in_(list(latest)))):
        flags[f.child_id].append({"kind": f.kind, "text": f.text})
    ms = defaultdict(dict)
    pairs = {(cid, cr.round_id) for cid, cr in latest.items()}
    for m in s.scalars(select(Measurement).where(Measurement.child_id.in_(list(latest)),
                                                 Measurement.field.in_(list(TESTS)))):
        if (m.child_id, m.round_id) in pairs:
            ms[m.child_id][m.field] = m
    prev = _prev_composite(s, latest)
    rows = []
    ql = (q or "").lower().strip()
    for cid, cr in latest.items():
        k = kids[cid]
        if ql and ql not in k.name.lower() and ql not in (k.parent or "").lower() and ql != cid.lower():
            continue
        if school and cr.school_id not in school.split(","):
            continue
        if coach and schools[cr.school_id].trainer_id != int(coach):
            continue
        if klass and cr.klass not in klass.split(","):
            continue
        if gender and k.gender != gender:
            continue
        if age_min is not None and (cr.age is None or cr.age < age_min):
            continue
        if age_max is not None and (cr.age is None or int(cr.age) > age_max):
            continue
        kinds = {f["kind"] for f in flags[cid]}
        if flag and not set(flag.split(",")) & kinds:
            continue
        tests = {}
        for f, m in ms[cid].items():
            tests[f] = {"value": m.value, "percentile": m.percentile, "status": m.status}
        rows.append({"id": cid, "name": k.name, "gender": k.gender, "klass": cr.klass,
                     "age": cr.age, "school_id": cr.school_id, "school": schools[cr.school_id].short,
                     "composite": cr.composite, "tests": tests, "flags": flags[cid],
                     "trend": round(cr.composite - prev[cid], 1)
                     if cid in prev and cr.composite is not None else None})

    def key(r):
        if test and test in TESTS:
            p = r["tests"].get(test, {}).get("percentile")
            v = p if (p is not None and r["tests"][test]["status"] in VALID) else None
        else:
            v = r["composite"]
        if sort == "name":
            return (r["name"].lower(),)
        if sort == "improved":
            return (r["trend"] is None, -(r["trend"] or 0))
        if sort == "worst":
            return (v is None, v if v is not None else 0)
        return (v is None, -(v or 0))
    rows.sort(key=key)
    return {"total": len(rows), "rows": rows[offset:offset + limit]}


def cite(s, m: Measurement, uploads=None) -> dict:
    r = s.get(Record, m.record_id)
    u = (uploads or {}).get(r.upload_id) or s.get(Upload, r.upload_id)
    return {"record_id": r.id, "file": u.filename, "sheet": r.sheet, "cell": m.cell, "row": r.row,
            "raw": m.raw}


def child_detail(s, cid: str, allowed) -> dict | None:
    k = s.get(Child, cid)
    if k is None or (allowed is not None and k.school_id not in allowed):
        return None
    users = {u.id: u for u in s.scalars(select(User))}
    sch = s.get(School, k.school_id)
    rmap = {r.id: r for r in rounds(s)}
    uploads = {u.id: u for u in s.scalars(select(Upload))}
    crs = sorted(s.scalars(select(ChildRound).where(ChildRound.child_id == cid)),
                 key=lambda c: rmap[c.round_id].test_date)
    ms = defaultdict(dict)
    for m in s.scalars(select(Measurement).where(Measurement.child_id == cid)):
        ms[m.round_id][m.field] = m
    out_rounds = []
    for cr in crs:
        tests = {}
        for f, m in ms[cr.round_id].items():
            tests[f] = {"value": m.value, "raw": m.raw, "unit": ALL[f].unit, "status": m.status,
                        "note": m.note, "percentile": m.percentile, "pool": m.pool,
                        "cite": cite(s, m, uploads)}
        out_rounds.append({**round_dict(rmap[cr.round_id]), "composite": cr.composite,
                           "age": cr.age, "klass": cr.klass, "tests": tests})
    names = sorted({r.name for r in s.scalars(select(Record).where(Record.child_id == cid))} - {k.name})
    flags = [{"kind": f.kind, "text": f.text, "evidence": f.evidence}
             for f in s.scalars(select(Flag).where(Flag.child_id == cid))]
    achievements = []
    for res, item, ev in s.execute(select(Result, EventItem, Event).join(EventItem, Result.item_id == EventItem.id)
                                   .join(Event, EventItem.event_id == Event.id).where(Result.child_id == cid)):
        achievements.append({"event": ev.title, "event_id": ev.id, "date": ev.start_date.isoformat(),
                             "level": ev.level, "item": f"{item.name} ({item.gender})",
                             "position": res.position, "mark": res.mark, "note": res.note})
    selections = []
    for sel, item, ev in s.execute(select(Selection, EventItem, Event).join(EventItem, Selection.item_id == EventItem.id)
                                   .join(Event, EventItem.event_id == Event.id).where(Selection.child_id == cid)):
        selections.append({"event": ev.title, "event_id": ev.id, "date": ev.start_date.isoformat(),
                           "item": f"{item.name} ({item.gender})", "status": sel.status})
    issues = [issue_dict(i) for i in s.scalars(select(Issue).where(Issue.child_id == cid,
                                                                   Issue.resolved.is_(False)))]
    progress = {}
    if len(out_rounds) >= 2:
        a, b = out_rounds[0]["tests"], out_rounds[-1]["tests"]
        for f in TESTS:
            if f in a and f in b and a[f]["value"] and b[f]["value"] \
                    and a[f]["status"] in VALID and b[f]["status"] in VALID:
                d = b[f]["value"] - a[f]["value"]
                better = d < 0 if TESTS[f].lower_is_better else d > 0
                progress[f] = {"from": a[f]["value"], "to": b[f]["value"], "delta": round(d, 2),
                               "pct": round(100 * d / a[f]["value"], 1), "better": better}
    return {"id": k.id, "name": k.name, "aliases": names, "parent": k.parent,
            "dob": k.dob.isoformat() if k.dob else None, "gender": k.gender, "klass": k.klass,
            "school": school_brief(sch, users), "rounds": out_rounds, "flags": flags,
            "achievements": achievements, "selections": selections, "issues": issues,
            "progress": progress}


def receipt(s, record_id: int, field: str | None, allowed, radius: int = 3, col: str | None = None) -> dict | None:
    """The cited spreadsheet row with its neighbours, as the trainer typed it."""
    r = s.get(Record, record_id)
    if r is None or (allowed is not None and r.school_id not in allowed):
        return None
    u = s.get(Upload, r.upload_id)
    sheet = u.sheets.get(r.sheet, {})
    near = s.scalars(select(Record).where(Record.upload_id == r.upload_id, Record.sheet == r.sheet,
                                          Record.row.between(r.row - radius, r.row + radius))
                     .order_by(Record.row)).all()
    col = (r.cells.get(field, {}).get("col") if field else None) or col
    twin = s.get(Record, r.twin_id) if r.twin_id else None
    return {"file": u.filename, "sha256": u.sha256, "uploaded_at": u.uploaded_at.isoformat(),
            "round": round_dict(s.get(Round, u.round_id)), "sheet": r.sheet,
            "header_row": sheet.get("header_row", 1), "headers": sheet.get("headers", []),
            "row": r.row, "col": col, "field": field,
            "rows": [{"row": x.row, "cells": x.raw_row, "cited": x.id == r.id} for x in near],
            "twin": {"sheet": twin.sheet, "row": twin.row, "headers": u.sheets.get(twin.sheet, {}).get("headers", []),
                     "cells": twin.raw_row} if twin else None}


# ------------------------------------------------------------------ overview / schools

def _avg_by_round(s, allowed) -> list[dict]:
    """Programme progress: mean raw value per test per round, plus mean composite."""
    rmap = {r.id: r for r in rounds(s)}
    crs = s.scalars(_scope(select(ChildRound), ChildRound.school_id, allowed)).all()
    ok = {(c.child_id, c.round_id) for c in crs}
    acc = defaultdict(lambda: defaultdict(list))
    for m in s.scalars(select(Measurement).where(Measurement.field.in_(list(TESTS)))):
        if (m.child_id, m.round_id) in ok and m.status in VALID and m.value is not None:
            acc[m.round_id][m.field].append(m.value)
    comp = defaultdict(list)
    for c in crs:
        if c.composite is not None:
            comp[c.round_id].append(c.composite)
    out = []
    for rid in sorted(acc, key=lambda r: rmap[r].test_date):
        out.append({**round_dict(rmap[rid]), "children": len({c.child_id for c in crs if c.round_id == rid}),
                    **{f: round(mean(v), 3) for f, v in acc[rid].items()}})
    return out


def overview(s, allowed, today: dt.date | None = None) -> dict:
    today = today or dt.date.today()
    latest = latest_by_child(s, allowed)
    flags = defaultdict(list)
    for f in s.scalars(select(Flag).where(Flag.child_id.in_(list(latest)))):
        flags[f.kind].append(f)
    kids = {c.id: c for c in s.scalars(select(Child).where(Child.id.in_(list(latest))))}
    schools = {x.id: x for x in s.scalars(select(School))}

    def brief(f: Flag) -> dict:
        k, cr = kids[f.child_id], latest[f.child_id]
        return {"id": k.id, "name": k.name, "klass": cr.klass, "gender": k.gender,
                "school": schools[cr.school_id].short, "school_id": cr.school_id,
                "composite": cr.composite, "text": f.text}
    lists = {kind: [brief(f) for f in sorted(fl, key=lambda f: -f.weight)[:8]]
             for kind, fl in flags.items()}
    counts = {kind: len({f.child_id for f in fl}) for kind, fl in flags.items()}
    iq = _scope(select(Issue).where(Issue.resolved.is_(False)), Issue.school_id, allowed)
    issues = s.scalars(iq).all()
    inbox = Counter(i.severity for i in issues)
    progress = _avg_by_round(s, allowed)
    change = {}
    if len(progress) >= 2:
        a, b = progress[0], progress[-1]
        for f in TESTS:
            if f in a and f in b and a[f]:
                d = (b[f] - a[f]) / a[f] * 100
                change[f] = {"pct": round(d, 1), "better": (d < 0) if TESTS[f].lower_is_better else (d > 0),
                             "from": a[f], "to": b[f]}
    ev = upcoming(s, today, 5)
    todos = [todo_dict(t) for t in s.scalars(select(Todo).where(Todo.done.is_(False))
                                              .order_by(Todo.due_date).limit(6))]
    sids = sorted({c.school_id for c in latest.values()})
    by_school = {sid: _avg_by_round(s, {sid}) for sid in sids}
    return {"children": len(latest), "schools": len(sids), "progress_by_school": by_school,
            "school_names": {x.id: x.short for x in schools.values() if x.id in sids},
            "flag_counts": counts, "lists": lists,
            "inbox": {"open": len(issues), **inbox}, "progress": progress, "change": change,
            "events": ev, "todos": todos, "rounds": [round_dict(r) for r in rounds(s)]}


def schools_summary(s, allowed) -> list[dict]:
    users = {u.id: u for u in s.scalars(select(User))}
    latest = latest_by_child(s, allowed)
    by_school = defaultdict(list)
    for cr in latest.values():
        by_school[cr.school_id].append(cr)
    flags = defaultdict(Counter)
    for f in s.scalars(select(Flag).where(Flag.child_id.in_(list(latest)))):
        flags[latest[f.child_id].school_id][f.kind] += 1
    pct = defaultdict(lambda: defaultdict(list))
    pairs = {(cid, cr.round_id): cr.school_id for cid, cr in latest.items()}
    for m in s.scalars(select(Measurement).where(Measurement.field.in_(list(TESTS)))):
        sid = pairs.get((m.child_id, m.round_id))
        if sid and m.percentile is not None and m.status in VALID:
            pct[sid][m.field].append(m.percentile)
    issues = Counter(i.school_id for i in s.scalars(select(Issue).where(Issue.resolved.is_(False))))
    out = []
    for x in s.scalars(_scope(select(School), School.id, allowed)):
        crs = by_school.get(x.id, [])
        comps = [c.composite for c in crs if c.composite is not None]
        out.append({**school_brief(x, users), "children": len(crs),
                    "composite": round(median(comps), 1) if comps else None,
                    "skills": {f: round(median(v), 1) for f, v in pct[x.id].items()},
                    "flags": dict(flags[x.id]), "issues": issues.get(x.id, 0),
                    "classes": sorted({c.klass for c in crs}, key=lambda k: (len(k), k))})
    return sorted(out, key=lambda x: -(x["composite"] or 0))


def school_detail(s, sid: str, allowed) -> dict | None:
    if allowed is not None and sid not in allowed:
        return None
    x = s.get(School, sid)
    if x is None:
        return None
    summ = next(o for o in schools_summary(s, {sid}))
    latest = latest_by_child(s, {sid})
    classes = defaultdict(list)
    for cr in latest.values():
        classes[cr.klass].append(cr.composite)
    cls = [{"klass": k, "children": len(v),
            "composite": round(median([c for c in v if c is not None]), 1) if any(c is not None for c in v) else None}
           for k, v in sorted(classes.items(), key=lambda kv: (len(kv[0]), kv[0]))]
    return {**summ, "progress": _avg_by_round(s, {sid}), "classes_detail": cls,
            "top": children(s, {sid}, sort="best", limit=5)["rows"],
            "push": children(s, {sid}, flag="push", sort="worst", limit=5)["rows"]}


# ------------------------------------------------------------------ inbox

def issue_dict(i: Issue) -> dict:
    return {"key": i.key, "kind": i.kind, "severity": i.severity, "school_id": i.school_id,
            "upload_id": i.upload_id, "child_id": i.child_id, "field": i.field, "title": i.title,
            "detail": i.detail, "record_ids": i.record_ids[:30], "options": i.options,
            "count": i.count, "resolved": i.resolved, "resolution": i.resolution}


SEV = {"high": 0, "medium": 1, "low": 2}


def inbox(s, allowed, status="open", kind=None, school=None) -> dict:
    q = _scope(select(Issue), Issue.school_id, allowed)
    all_issues = s.scalars(q).all()
    counts = Counter(i.kind for i in all_issues if not i.resolved)
    rows = [i for i in all_issues if (i.resolved == (status == "resolved"))
            and (not kind or i.kind == kind) and (not school or i.school_id == school)]
    rows.sort(key=lambda i: (SEV[i.severity], i.kind, i.id))
    return {"counts": dict(counts), "open": sum(counts.values()),
            "resolved": sum(1 for i in all_issues if i.resolved),
            "rows": [issue_dict(i) for i in rows]}


# ------------------------------------------------------------------ events

def upcoming(s, today: dt.date, n=5) -> list[dict]:
    evs = s.scalars(select(Event).where(Event.start_date >= today).order_by(Event.start_date).limit(n))
    return [event_brief(s, e) for e in evs]


def event_brief(s, e: Event) -> dict:
    items = s.scalars(select(EventItem).where(EventItem.event_id == e.id)).all()
    ids = [i.id for i in items]
    picked = Counter(sel.item_id for sel in s.scalars(select(Selection).where(
        Selection.item_id.in_(ids), Selection.status == "selected"))) if ids else Counter()
    slots = sum(i.slots for i in items)
    todos = s.scalars(select(Todo).where(Todo.event_id == e.id)).all()
    return {"id": e.id, "title": e.title, "kind": e.kind, "level": e.level,
            "start_date": e.start_date.isoformat(),
            "end_date": e.end_date.isoformat() if e.end_date else None, "start_time": e.start_time,
            "venue": e.venue, "notes": e.notes, "school_ids": e.school_ids, "items": len(items),
            "slots": slots, "picked": sum(min(picked[i.id], i.slots) for i in items),
            "todos": len(todos), "todos_done": sum(1 for t in todos if t.done)}


def event_detail(s, eid: int) -> dict | None:
    e = s.get(Event, eid)
    if e is None:
        return None
    items = []
    kids = {}
    for it in s.scalars(select(EventItem).where(EventItem.event_id == eid).order_by(EventItem.id)):
        sels = s.scalars(select(Selection).where(Selection.item_id == it.id).order_by(Selection.status, Selection.rank)).all()
        res = {r.child_id: r for r in s.scalars(select(Result).where(Result.item_id == it.id))}
        rows = []
        for sel in sels:
            k = kids.get(sel.child_id) or s.get(Child, sel.child_id)
            kids[sel.child_id] = k
            r = res.get(sel.child_id)
            rows.append({"child_id": k.id, "name": k.name, "klass": k.klass, "gender": k.gender,
                         "school_id": k.school_id, "status": sel.status, "rank": sel.rank,
                         "summary": sel.reason.get("summary", ""),
                         "result": {"position": r.position, "mark": r.mark, "note": r.note} if r else None})
        items.append({"id": it.id, "name": it.name, "discipline": it.discipline, "gender": it.gender,
                      "age_min": it.age_min, "age_max": it.age_max, "slots": it.slots,
                      "reserves": it.reserves, "selections": rows})
    todos = [todo_dict(t) for t in s.scalars(select(Todo).where(Todo.event_id == eid).order_by(Todo.done, Todo.due_date))]
    return {**event_brief(s, e), "items_detail": items, "todo_list": todos}


def todo_dict(t: Todo) -> dict:
    return {"id": t.id, "event_id": t.event_id, "text": t.text, "done": t.done,
            "due_date": t.due_date.isoformat() if t.due_date else None}
