"""Upload -> records -> identity -> rebuild (measurements, percentiles, flags, Inbox).

Rules only, no model: the same files and the same decisions always give the same output.
rebuild() recomputes every derived table from the stored records and the coordinator's
resolutions, so a new upload or a decision simply re-runs it.
"""

import datetime as dt
import hashlib
import re
from collections import Counter, defaultdict
from statistics import median

import numpy as np
from rapidfuzz import fuzz
from sqlalchemy import delete, func, select

from ti import clean, config, identity, ingest
from ti.db import (DERIVED, Child, ChildRound, Flag, Issue, Measurement, Record, Resolution,
                   Round, School, Setting, Upload)
from ti.template import ALL, TESTS, class_number

VALID = {"ok", "repaired", "corrected", "accepted"}

DEFAULTS = {
    "weights": {"jump": 1.0, "ball": 1.0, "shuttle": 1.0, "relay": 1.0},
    "flags": {"top": 85, "top_skill": 95, "push": 20, "improved": 12, "declining": 12,
              "skill_drop": 25},
    "placeholder_share": 0.25,
}


def settings(s) -> dict:
    row = s.get(Setting, "programme")
    out = {k: (dict(v) if isinstance(v, dict) else v) for k, v in DEFAULTS.items()}
    if row:
        for k, v in row.value.items():
            out[k] = {**out[k], **v} if isinstance(out.get(k), dict) else v
    return out


# ------------------------------------------------------------------ upload

class Refused(ValueError):
    pass


def slug(name: str) -> str:
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", name.lower())).strip("-")[:60]


def school_for(s, name: str, cache: dict) -> School | None:
    if not name:
        return None
    if name in cache:
        return cache[name]
    sch = s.scalar(select(School).where(School.name == name))
    if sch is None:
        for other in s.scalars(select(School)):
            if fuzz.token_set_ratio(other.name.lower(), name.lower()) >= 92:
                sch = other
                break
    if sch is None:
        short = re.sub(r"\b(primary|upper|high|school|schools|scl|govt|government)\b", "", name,
                       flags=re.I).strip(" ,")
        sch = School(id=slug(name), name=name, short=short or name,
                     hue=(hash(name) % 12) * 30)
        s.add(sch)
        s.flush()
    cache[name] = sch
    return sch


def ingest_upload(s, data: bytes, filename: str, round_id: int, user_id=None) -> Upload:
    sha = hashlib.sha256(data).hexdigest()
    dup = s.scalar(select(Upload).where(Upload.sha256 == sha, Upload.round_id == round_id,
                                        Upload.status == "accepted"))
    if dup:
        raise Refused(f"This exact file was already uploaded for this round on "
                      f"{dup.uploaded_at:%d %b %Y}.")
    sheets = ingest.read(data, filename)
    if not sheets:
        raise Refused("No sheet in this file has the assessment template headers "
                      "(School, Class, Student Name and at least one test).")
    config.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "xlsx"
    path = config.UPLOAD_DIR / f"{sha[:16]}.{ext}"
    path.write_bytes(data)
    up = Upload(filename=filename, sha256=sha, size=len(data), stored_path=str(path),
                round_id=round_id, uploaded_by=user_id,
                sheets={sh.name: {"header_row": sh.header_row, "headers": sh.headers,
                                  "cols": sh.cols, "rows": len(sh.rows),
                                  "preferred": sh.preferred} for sh in sheets})
    s.add(up)
    s.flush()
    cache: dict = {}
    pref_ids: list[int] = []
    best = next(sh for sh in sheets if sh.preferred)
    for sh in sorted(sheets, key=lambda x: not x.preferred):     # preferred sheet first
        for i, r in enumerate(sh.rows):
            sch = school_for(s, r.school, cache)
            rec = Record(upload_id=up.id, sheet=r.sheet, row=r.row, preferred=r.preferred,
                         school_id=sch.id if sch else None, klass=r.klass, name=r.name,
                         parent=r.parent, dob=r.dob, gender=r.gender,
                         cells={**r.cells, **({"_dob": {"note": r.dob_note}} if r.dob_note else {})},
                         raw_row=r.raw_row)
            s.add(rec)
            s.flush()
            if sh is best:
                pref_ids.append(rec.id)
            elif r.twin is not None and r.twin < len(pref_ids):
                rec.twin_id = pref_ids[r.twin]
                tw = s.get(Record, pref_ids[r.twin])
                tw.twin_id = rec.id
    link(s, up)
    n = len(best.rows)
    up.summary = {"rows": n, "sheets": len(sheets),
                  "schools": sorted({r.school for r in best.rows if r.school})}
    rebuild(s)
    up.summary = {**up.summary, **upload_stats(s, up.id)}
    s.commit()
    return up


def upload_stats(s, upload_id: int) -> dict:
    recs = s.scalars(select(Record).where(Record.upload_id == upload_id, Record.preferred)).all()
    st = Counter(r.link_status for r in recs)
    issues = s.scalar(select(func.count()).select_from(Issue).where(Issue.upload_id == upload_id))
    return {"linked": st["exact"] + st["fuzzy"] + st["confirmed"], "new": st["new"],
            "review": st["review"], "issues": issues or 0}


def next_child_id(s) -> str:
    last = s.scalar(select(func.max(Child.id)))
    return f"C{(int(last[1:]) + 1 if last else 1):05d}"


def link(s, up: Upload) -> None:
    recs = s.scalars(select(Record).where(Record.upload_id == up.id, Record.preferred,
                                          Record.school_id.is_not(None)).order_by(Record.id)).all()
    schools = {r.school_id for r in recs}
    kids = s.scalars(select(Child).where(Child.school_id.in_(schools))).all()
    same_round = s.scalars(select(Record.child_id).join(Upload).where(
        Upload.round_id == up.round_id, Upload.id != up.id, Record.child_id.is_not(None))).all()
    claimed = set(same_round)
    keyed = {identity.exact_key(c.school_id, c.name, c.parent, c.dob): c for c in kids}
    # Also key children by every name they were written with before.
    for r in s.scalars(select(Record).where(Record.child_id.is_not(None),
                                            Record.school_id.in_(schools))):
        keyed.setdefault(identity.exact_key(r.school_id, r.name, r.parent, r.dob),
                         s.get(Child, r.child_id))
    created: set[str] = set()
    pending = []
    for r in recs:
        c = keyed.get(identity.exact_key(r.school_id, r.name, r.parent, r.dob))
        if c is not None:
            r.child_id, r.link_status, r.link_score = c.id, "exact", 100.0
            claimed.add(c.id)
        else:
            pending.append(r)
    for r in pending:
        k = identity.exact_key(r.school_id, r.name, r.parent, r.dob)
        if k in keyed:                         # a duplicate of a child created just now
            c = keyed[k]
            r.child_id, r.link_status, r.link_score = c.id, "exact", 100.0
            continue
        cands = [c for c in kids if c.school_id == r.school_id and c.id not in claimed
                 and c.id not in created]
        status, c, sc, cl = identity.best_match(r, cands)
        r.link_score, r.link_candidates = sc, cl
        if status == "fuzzy":
            r.child_id, r.link_status = c.id, "fuzzy"
            claimed.add(c.id)
            keyed[k] = c
        elif status == "review":
            r.link_status = "review"
        else:
            c = new_child(s, r)
            kids.append(c)
            created.add(c.id)
            keyed[k] = c
            r.link_status = "new"
    s.flush()


def new_child(s, r: Record) -> Child:
    c = Child(id=next_child_id(s), school_id=r.school_id, name=r.name, parent=r.parent,
              dob=r.dob, gender=r.gender, klass=r.klass)
    s.add(c)
    s.flush()
    r.child_id = c.id
    return c


# ------------------------------------------------------------------ rebuild

class Builder:
    def __init__(self, s):
        self.s = s
        self.cfg = settings(s)
        self.res = {r.key: r.payload for r in s.scalars(select(Resolution))}
        self.rounds = {r.id: r for r in s.scalars(select(Round))}
        self.uploads = {u.id: u for u in s.scalars(select(Upload).where(Upload.status == "accepted"))}
        self.schools = {x.id: x for x in s.scalars(select(School))}
        self.kids = {c.id: c for c in s.scalars(select(Child))}
        recs = s.scalars(select(Record).where(Record.upload_id.in_(self.uploads))).all()
        self.recs = {r.id: r for r in recs}
        self.pref = [r for r in recs if r.preferred]
        self.issues: dict[str, Issue] = {}
        self.excluded: set[int] = set()
        self.cell_override: dict[tuple[int, str], tuple[str, str]] = {}   # -> (status, note)

    # -- helpers
    def round_of(self, r: Record) -> int:
        return self.uploads[r.upload_id].round_id

    def where(self, r: Record, field: str | None = None) -> str:
        u = self.uploads[r.upload_id]
        col = r.cells.get(field, {}).get("col", "") if field else ""
        return f"{u.filename} › {r.sheet} › {col}{r.row}" if col else f"{u.filename} › {r.sheet} › row {r.row}"

    def issue(self, key, **kw) -> Issue:
        if key in self.issues:
            return self.issues[key]
        i = Issue(key=key, **kw)
        self.issues[key] = i
        return i

    def label(self, r: Record) -> str:
        return f"{r.name} ({r.klass})"

    # -- checks over groups of rows
    def class_copies(self):
        groups = defaultdict(list)
        for r in self.pref:
            groups[(r.upload_id, r.school_id)].append(r)
        for (u, sch), rows in groups.items():
            by_class = defaultdict(dict)
            for r in rows:
                by_class[r.klass].setdefault(clean.name_key(r.name), r)
            classes = sorted(by_class, key=lambda k: class_number(k) or 0)
            for i, a in enumerate(classes):
                for b in classes[i + 1:]:
                    common = by_class[a].keys() & by_class[b].keys()
                    small = min(len(by_class[a]), len(by_class[b]))
                    if len(common) < 5 or len(common) / small < 0.6:
                        continue
                    key = f"classcopy:{u}:{sch}:{a}:{b}"
                    choice = self.res.get(key, {})
                    drop = choice.get("drop", b)
                    if not choice.get("keep_both"):
                        self.excluded |= {by_class[drop][n].id for n in common}
                    ra = [by_class[a][n].row for n in common]
                    rb = [by_class[b][n].row for n in common]
                    self.issue(
                        key, kind="class_copy", severity="high", school_id=sch, upload_id=u,
                        title=f"{len(common)} children appear in both {a} and {b}",
                        detail=(f"Rows {min(rb)}–{max(rb)} ({b}) repeat the names in rows "
                                f"{min(ra)}–{max(ra)} ({a}) of {self.uploads[u].filename}. "
                                f"This looks like a class block pasted twice. Until you decide, "
                                f"the {drop} copies are left out."),
                        record_ids=[by_class[b][n].id for n in sorted(common)][:200],
                        count=len(common),
                        options=[{"id": "keep_a", "label": f"Children are in {a}", "payload": {"drop": b}},
                                 {"id": "keep_b", "label": f"Children are in {b}", "payload": {"drop": a}},
                                 {"id": "both", "label": "They are different children", "payload": {"keep_both": True}}])

    def placeholders(self):
        share = self.cfg["placeholder_share"]
        groups = defaultdict(list)
        for r in self.pref:
            if r.id in self.excluded:
                continue
            for f in TESTS:
                c = r.cells.get(f)
                if c and c.get("v") is not None:
                    groups[(r.upload_id, r.school_id, f)].append((r, c["v"]))
        for (u, sch, f), vals in groups.items():
            if len(vals) < 15:
                continue
            v, n = Counter(v for _, v in vals).most_common(1)[0]
            if n / len(vals) < share or n < 8:
                continue
            key = f"placeholder:{u}:{sch}:{f}:{v:g}"
            accepted = self.res.get(key, {}).get("accept")
            if not accepted:
                for r, x in vals:
                    if x == v:
                        self.cell_override[(r.id, f)] = (
                            "suspect", f"{v:g} {TESTS[f].unit} was entered for {n} of {len(vals)} "
                                       f"children in this school; likely a placeholder")
            t = TESTS[f]
            self.issue(key, kind="placeholder", severity="medium", school_id=sch, upload_id=u,
                       field=f, count=n,
                       title=f"{t.label} {v:g} {t.unit} entered for {n} of {len(vals)} children",
                       detail=(f"The same {t.label.lower()} value appears for {n / len(vals):.0%} of "
                               f"{self.schools[sch].short} in {self.uploads[u].filename}. Real "
                               f"results vary; this looks like a default typed in. These values "
                               f"are left out of rankings and shortlists until you accept them."),
                       record_ids=[r.id for r, x in vals if x == v][:200],
                       options=[{"id": "accept", "label": "Values are real, use them", "payload": {"accept": True}},
                                {"id": "exclude", "label": "Keep them out", "payload": {"accept": False}}])

    def relay_units(self):
        groups = defaultdict(list)
        for r in self.pref + [x for x in self.recs.values() if not x.preferred]:
            c = r.cells.get("relay")
            if c and c.get("v") is not None:
                groups[(r.upload_id, r.school_id)].append((r, c["v"]))
        for (u, sch), vals in groups.items():
            med = median(v for _, v in vals)
            if med >= 9 or len(vals) < 10:
                continue
            ints = sum(1 for _, v in vals if float(v).is_integer()) / len(vals)
            kind = "levels or laps" if ints > 0.6 else "minutes"
            for r, _ in vals:
                self.cell_override[(r.id, "relay")] = (
                    "suspect", f"This school's relay column looks like {kind}, not seconds")
            key = f"relayunit:{u}:{sch}"
            self.issue(key, kind="unit", severity="medium", school_id=sch, upload_id=u,
                       field="relay", count=len(vals),
                       title=f"Relay column in {self.schools[sch].short} is not in seconds",
                       detail=(f"Typical value is {med:g}, while other schools record about 15–25 "
                               f"seconds. It looks like {kind}. Relay results from this school are "
                               f"shown but not compared with other schools."),
                       record_ids=[r.id for r, _ in vals][:200],
                       options=[{"id": "ok", "label": "Understood, keep apart", "payload": {"ok": True}}])

    def duplicates_summary(self, dup_rows):
        groups = defaultdict(list)
        for r in dup_rows:
            groups[(r.upload_id, r.school_id)].append(r)
        for (u, sch), rows in groups.items():
            rows.sort(key=lambda r: r.row)
            key = f"duprows:{u}:{sch}"
            self.issue(key, kind="duplicate_rows", severity="low", school_id=sch, upload_id=u,
                       count=len(rows),
                       title=f"{len(rows)} rows are exact repeats in {self.schools[sch].short}",
                       detail=(f"Rows {rows[0].row}–{rows[-1].row} of {self.uploads[u].filename} "
                               f"repeat children already entered with the same numbers. Each child "
                               f"is counted once."),
                       record_ids=[r.id for r in rows][:200],
                       options=[{"id": "ok", "label": "OK", "payload": {"ok": True}}])

    # -- measurements
    def build(self):
        s = self.s
        by_cr = defaultdict(list)
        for r in self.pref:
            if r.child_id and r.id not in self.excluded:
                by_cr[(r.child_id, self.round_of(r))].append(r)
        dup_rows = []
        self.ms: list[Measurement] = []
        for (cid, rid), rows in by_cr.items():
            rows.sort(key=lambda r: r.id)
            for f in ALL:
                cands = []
                for r in rows:
                    c = r.cells.get(f)
                    src = r
                    if (c is None or c.get("v") is None) and r.twin_id and r.twin_id in self.recs:
                        # e.g. relay only in Sheet1, or the revised sheet blanked a typing slip
                        tc = self.recs[r.twin_id].cells.get(f)
                        if tc is not None and (c is None or tc.get("v") is not None):
                            src, c = self.recs[r.twin_id], tc
                    if c is not None:
                        cands.append((src, c))
                if not cands:
                    continue
                with_v = [(r, c) for r, c in cands if c.get("v") is not None]
                distinct = {c["v"] for _, c in with_v}
                if len(distinct) > 1:
                    m = self.conflict(cid, rid, f, with_v)
                elif with_v:
                    m = self.cell(cid, rid, f, *with_v[0])
                else:
                    m = self.cell(cid, rid, f, *cands[0])
                if m:
                    self.ms.append(m)
            if len(rows) > 1:
                same = all(all(a.cells.get(f, {}).get("v") == rows[0].cells.get(f, {}).get("v")
                               for f in TESTS) for a in rows[1:])
                if same:
                    dup_rows.extend(rows[1:])
            self.sheet_disagreements(rows)
            for r in rows:
                note = r.cells.get("_dob", {}).get("note")
                if note:
                    key = f"dob:{r.id}"
                    self.issue(key, kind="dob", severity="low", school_id=r.school_id,
                               upload_id=r.upload_id, child_id=cid,
                               title=f"Date of birth unclear for {self.label(r)}",
                               detail=f"{note} ({self.where(r, 'dob')}). Age falls back to class.",
                               record_ids=[r.id],
                               options=[{"id": "ok", "label": "OK", "payload": {"ok": True}}])
        self.duplicates_summary(dup_rows)
        s.add_all(self.ms)
        s.flush()

    def cell(self, cid, rid, f, r: Record, c: dict) -> Measurement:
        status, note, v = c.get("status", "missing"), c.get("note", ""), c.get("v")
        if (r.id, f) in self.cell_override and status in VALID:
            status, note = self.cell_override[(r.id, f)]
        key = f"value:{r.id}:{f}"
        decision = self.res.get(key)
        if decision:
            a = decision.get("action")
            if a == "accept":
                status = "accepted"
            elif a == "correct":
                v, status, note = float(decision["value"]), "corrected", f"Corrected from {c.get('raw')}"
            elif a == "exclude":
                status = "excluded"
        if f in TESTS or f == "height":
            if c.get("status") == "suspect" and (r.id, f) not in self.cell_override:
                self.suspect_issue(cid, r, f, c, key)
            elif c.get("status") == "repaired":
                self.issue(key, kind="repaired", severity="low", school_id=r.school_id,
                           upload_id=r.upload_id, child_id=cid, field=f,
                           title=f"{ALL[f].label} fixed for {self.label(r)}",
                           detail=f"{c.get('note')} ({self.where(r, f)}).", record_ids=[r.id],
                           options=[{"id": "ok", "label": "Looks right", "payload": {"action": "accept"}},
                                    {"id": "exclude", "label": "Leave it out", "payload": {"action": "exclude"}}])
        return Measurement(child_id=cid, round_id=rid, field=f, value=v, raw=str(c.get("raw", ""))[:80],
                           status=status, note=note[:300], record_id=r.id,
                           cell=f"{c.get('col', '')}{r.row}")

    def suspect_issue(self, cid, r, f, c, key):
        t = ALL[f]
        hint = clean.unit_hint(f, c["v"])
        opts = [{"id": "accept", "label": "Value is right", "payload": {"action": "accept"}}]
        if hint:
            opts.append({"id": "fix", "label": f"Use {hint[0]:g} {t.unit}",
                         "payload": {"action": "correct", "value": hint[0]}})
        opts += [{"id": "correct", "label": "Enter the right value", "input": "number",
                  "payload": {"action": "correct"}},
                 {"id": "exclude", "label": "Leave it out", "payload": {"action": "exclude"}}]
        self.issue(key, kind="implausible", severity="medium", school_id=r.school_id,
                   upload_id=r.upload_id, child_id=cid, field=f,
                   title=f"{t.label} {c['raw']} {t.unit} for {self.label(r)} looks wrong",
                   detail=f"{c.get('note')}. Cell {self.where(r, f)}.", record_ids=[r.id],
                   options=opts)

    def conflict(self, cid, rid, f, with_v) -> Measurement:
        key = f"pick:{cid}:{rid}:{f}"
        pick = self.res.get(key, {})
        t = ALL[f]
        chosen = next(((r, c) for r, c in with_v if r.id == pick.get("record_id")), None)
        if chosen:
            m = self.cell(cid, rid, f, *chosen)
            if m.status in VALID or m.status == "suspect":
                m.note = "Chosen by coordinator between entries"
        else:
            m = self.cell(cid, rid, f, *with_v[0])
            m.status = "excluded" if pick.get("exclude") else "disputed"
            m.note = "Two entries disagree: " + " vs ".join(f"{c['raw']}" for _, c in with_v)
        if f in TESTS:
            r0 = with_v[0][0]
            self.issue(key, kind="conflict", severity="high", school_id=r0.school_id,
                       upload_id=r0.upload_id, child_id=cid, field=f,
                       title=f"{t.label} entered twice for {self.label(r0)} with different values",
                       detail=" · ".join(f"{c['raw']} {t.unit} in {self.where(r, f)}" for r, c in with_v)
                       + ". Neither is used until you pick one.",
                       record_ids=[r.id for r, _ in with_v],
                       options=[{"id": f"r{r.id}", "label": f"Use {c['raw']} {t.unit} (row {r.row})",
                                 "payload": {"record_id": r.id}} for r, c in with_v]
                       + [{"id": "exclude", "label": "Neither", "payload": {"exclude": True}}])
        return m

    def sheet_disagreements(self, rows):
        for r in rows:
            if not r.twin_id or r.twin_id not in self.recs:
                continue
            o = self.recs[r.twin_id]
            for f in TESTS:
                a, b = r.cells.get(f), o.cells.get(f)
                if not a or not b or a.get("raw") == b.get("raw"):
                    continue
                if a.get("v") == b.get("v"):
                    continue
                key = f"sheet:{r.id}:{f}"
                t = TESTS[f]
                self.issue(key, kind="sheet_disagree", severity="low", school_id=r.school_id,
                           upload_id=r.upload_id, child_id=r.child_id, field=f,
                           title=f"{r.sheet} and {o.sheet} disagree on {t.label.lower()} for {self.label(r)}",
                           detail=(f"{r.sheet}: “{a.get('raw') or 'blank'}” ({self.where(r, f)}) · "
                                   f"{o.sheet}: “{b.get('raw') or 'blank'}” ({self.where(o, f)}). "
                                   f"{r.sheet} is used."),
                           record_ids=[r.id, o.id],
                           options=[{"id": "ok", "label": f"{r.sheet} is right", "payload": {"ok": True}}])

    # -- age-relative outliers and percentiles
    def ages(self):
        """Age at each round from DOB; when DOB and class disagree by years, trust the class."""
        self.age = {}
        for cid, kid in self.kids.items():
            n = class_number(kid.klass) if kid.klass else None
            for rid, rnd in self.rounds.items():
                a = clean.age_on(kid.dob, rnd.test_date)
                expect = n + 5.5 if n else None
                if expect is not None and a is not None and abs(a - expect) > 2.6:
                    key = f"agefit:{cid}"
                    if not self.res.get(key, {}).get("dob_ok"):
                        recs = [r for r in self.pref if r.child_id == cid]
                        r0 = recs[0] if recs else None
                        self.issue(key, kind="dob", severity="medium", school_id=kid.school_id,
                                   upload_id=r0.upload_id if r0 else None, child_id=cid, field="dob",
                                   title=f"Date of birth does not fit {kid.klass} for {kid.name}",
                                   detail=(f"Born {kid.dob:%d %b %Y}, so {a:.0f} years old, but children in "
                                           f"{kid.klass} are usually {n + 4}–{n + 6}. Percentiles use the "
                                           f"class age ({expect:.0f}) until you confirm the date."
                                           + (f" {self.where(r0, 'dob')}." if r0 else "")),
                                   record_ids=[r.id for r in recs][:5],
                                   options=[{"id": "class", "label": "Date is wrong, use class age", "payload": {"dob_ok": False}},
                                            {"id": "dob", "label": "Date is right", "payload": {"dob_ok": True}}])
                        a = expect
                if a is None and expect is not None:
                    a = expect
                self.age[(cid, rid)] = a

    def pools(self, f, rid, gender):
        return [m for m in self.ms if m.field == f and m.round_id == rid and m.value is not None
                and self.kids[m.child_id].gender == gender and self.age.get((m.child_id, rid))]

    def outliers(self):
        for f in TESTS:
            for rid in self.rounds:
                for g in ("Boys", "Girls"):
                    ms = [m for m in self.pools(f, rid, g) if m.status in VALID]
                    if len(ms) < 30:
                        continue
                    ages = np.array([self.age[(m.child_id, rid)] for m in ms])
                    vals = np.array([m.value for m in ms])
                    for i, m in enumerate(ms):
                        near = np.abs(ages - ages[i]) <= 1.0
                        if near.sum() < 15:
                            continue
                        med = float(np.median(vals[near]))
                        mad = float(np.median(np.abs(vals[near] - med))) * 1.4826 or 0.01
                        z = (m.value - med) / mad
                        if abs(z) < 4.5 or m.status in ("accepted", "corrected"):
                            continue
                        r = self.recs[m.record_id]
                        key = f"value:{r.id}:{f}"
                        if self.res.get(key):
                            continue
                        t = TESTS[f]
                        a = int(ages[i])
                        m.status = "suspect"
                        m.note = (f"Far from other {a}-year-old {g.lower()} "
                                  f"(typical {med:.2f} {t.unit})")
                        hint = clean.unit_hint(f, m.value)
                        if f == "jump" and m.value > med * 2.5 and not hint:
                            hint = (round(m.value * 0.3048, 2), "")
                        opts = [{"id": "accept", "label": "Value is right", "payload": {"action": "accept"}}]
                        if hint:
                            opts.append({"id": "fix", "label": f"Use {hint[0]:g} {t.unit} (feet → m)"
                                         if f == "jump" and m.value < 11 else f"Use {hint[0]:g} {t.unit}",
                                         "payload": {"action": "correct", "value": hint[0]}})
                        opts += [{"id": "correct", "label": "Enter the right value", "input": "number",
                                  "payload": {"action": "correct"}},
                                 {"id": "exclude", "label": "Leave it out", "payload": {"action": "exclude"}}]
                        self.issue(key, kind="outlier", severity="medium", school_id=r.school_id,
                                   upload_id=r.upload_id, child_id=m.child_id, field=f,
                                   title=f"{t.label} {m.raw} {t.unit} is unusual for {self.label(r)}",
                                   detail=(f"Other {a}-year-old {g.lower()} are typically "
                                           f"{med:.2f} {t.unit}. Cell {self.where(r, f)}. Left out "
                                           f"of rankings until you check it."),
                                   record_ids=[r.id], options=opts)

    def percentiles(self):
        for f in TESTS:
            lower = TESTS[f].lower_is_better
            for rid in self.rounds:
                for g in ("Boys", "Girls"):
                    ms = [m for m in self.pools(f, rid, g) if m.status in VALID]
                    if not ms:
                        continue
                    ages = np.array([self.age[(m.child_id, rid)] for m in ms])
                    vals = np.array([m.value for m in ms])
                    if lower:
                        vals = -vals
                    for i, m in enumerate(ms):
                        for width in (1.0, 1.5, 2.5, 99):
                            near = np.abs(ages - ages[i]) <= width
                            if near.sum() >= 25 or width == 99:
                                break
                        pool = vals[near]
                        pct = 100.0 * ((pool < vals[i]).sum() + 0.5 * (pool == vals[i]).sum()) / len(pool)
                        m.percentile = round(pct, 1)
                        lo, hi = int(ages[i] - width), int(ages[i] + width)
                        m.pool = (f"{len(pool)} {g.lower()} aged {int(ages[i])}" if width <= 1
                                  else f"{len(pool)} {g.lower()} aged {lo}–{hi}")

    def child_rounds(self):
        w = self.cfg["weights"]
        per = defaultdict(dict)
        for m in self.ms:
            per[(m.child_id, m.round_id)][m.field] = m
        self.cr = {}
        for (cid, rid), fs in per.items():
            rec = self.recs[next(iter(fs.values())).record_id]
            pcts = {f: fs[f].percentile for f in TESTS if f in fs and fs[f].percentile is not None}
            tot = sum(w.get(f, 1) for f in pcts)
            comp = round(sum(p * w.get(f, 1) for f, p in pcts.items()) / tot, 1) \
                if len(pcts) >= 2 and tot else None
            cr = ChildRound(child_id=cid, round_id=rid, school_id=rec.school_id, klass=rec.klass,
                            age=self.age.get((cid, rid)), composite=comp, n_tests=len(pcts))
            self.cr[(cid, rid)] = (cr, fs)
            self.s.add(cr)
        # keep the registry's class current
        latest = {}
        for (cid, rid), (cr, _) in self.cr.items():
            d = self.rounds[rid].test_date
            if cid not in latest or d > latest[cid][0]:
                latest[cid] = (d, cr.klass)
        for cid, (_, k) in latest.items():
            self.kids[cid].klass = k

    def flags(self):
        th = self.cfg["flags"]
        order = sorted(self.rounds, key=lambda r: self.rounds[r].test_date)
        school_rounds = defaultdict(set)
        recorded = defaultdict(set)      # (school, round) -> tests that school actually recorded
        for (cid, rid), (cr, fs) in self.cr.items():
            school_rounds[cr.school_id].add(rid)
            recorded[(cr.school_id, rid)] |= {f for f, m in fs.items() if m.value is not None}
        for cid, kid in self.kids.items():
            mine = [rid for rid in order if (cid, rid) in self.cr]
            if not mine:
                continue
            last = mine[-1]
            cr, fs = self.cr[(cid, last)]
            rl = self.rounds[last].label
            ev = lambda *fields: [fs[f].id for f in fields if f in fs]  # noqa: E731
            pct = {f: fs[f].percentile for f in TESTS if f in fs and fs[f].percentile is not None}
            a = int(cr.age) if cr.age else None
            who = f"{a}-year-old {kid.gender.lower()}" if a and kid.gender else "children their age"
            add = lambda kind, text, weight, evid: self.s.add(Flag(  # noqa: E731
                child_id=cid, kind=kind, text=text, weight=weight, evidence=evid))
            if cr.composite is not None and cr.composite >= th["top"]:
                add("top", f"Overall P{cr.composite:.0f} among {who} in {rl}", cr.composite, ev(*pct))
            else:
                best = [f for f, p in pct.items() if p >= th["top_skill"]]
                if best:
                    f = max(best, key=pct.get)
                    add("top", f"{TESTS[f].label} P{pct[f]:.0f} among {who} in {rl}", pct[f], ev(f))
            if cr.composite is not None and cr.composite <= th["push"]:
                weak = sorted(pct, key=pct.get)[:2]
                add("push", f"Overall P{cr.composite:.0f} among {who}; weakest: "
                    + ", ".join(f"{TESTS[f].label.lower()} P{pct[f]:.0f}" for f in weak),
                    100 - cr.composite, ev(*pct))
            if len(mine) >= 2:
                prev = mine[-2]
                pcr, pfs = self.cr[(cid, prev)]
                if cr.composite is not None and pcr.composite is not None:
                    d = cr.composite - pcr.composite
                    span = f"{self.rounds[prev].label.split()[0]} → {rl.split()[0]}"
                    common = [f for f in pct if f in pfs and pfs[f].percentile is not None]
                    evid = ev(*common) + [pfs[f].id for f in common]
                    if d >= th["improved"]:
                        add("improved", f"Up {d:.0f} points overall ({span})", d, evid)
                    elif d <= -th["declining"]:
                        add("declining", f"Down {-d:.0f} points overall ({span})", -d, evid)
                    else:
                        drops = [(pfs[f].percentile - pct[f], f) for f in common
                                 if pfs[f].percentile - pct[f] >= th["skill_drop"]]
                        if drops:
                            dd, f = max(drops)
                            add("declining", f"{TESTS[f].label} down {dd:.0f} points ({span})", dd,
                                [fs[f].id, pfs[f].id])
            latest_school = max(school_rounds[kid.school_id], key=lambda r: self.rounds[r].test_date)
            if latest_school != last:
                add("missing", f"Not in {self.rounds[latest_school].label} sheet", 1, [])
            else:
                gone = [f for f in TESTS if f in recorded[(cr.school_id, last)]
                        and (f not in fs or fs[f].value is None)]
                held = [f for f in TESTS if f in fs and fs[f].status in ("suspect", "disputed")]
                if gone:
                    add("missing", "No " + ", ".join(TESTS[f].label.lower() for f in gone) + f" in {rl}",
                        len(gone), ev(*gone))
                if held:
                    add("missing", ", ".join(TESTS[f].label for f in held) + " waiting for a data check",
                        len(held), ev(*held))

    def names(self):
        for r in self.pref:
            if r.link_status != "review" or r.child_id:
                continue
            key = f"name:{r.id}"
            opts = []
            for cid, sc in r.link_candidates:
                c = self.kids.get(cid)
                if c:
                    opts.append({"id": cid, "label": f"Same as {c.name} ({c.klass}, parent {c.parent or '—'})",
                                 "payload": {"child_id": cid}, "score": sc})
            opts.append({"id": "new", "label": "A different child", "payload": {"new": True}})
            self.issue(key, kind="name", severity="high", school_id=r.school_id, upload_id=r.upload_id,
                       title=f"Who is “{r.name}” ({r.klass})?",
                       detail=(f"Parent {r.parent or 'not given'}, born "
                               f"{r.dob:%d %b %Y}. " if r.dob else f"Parent {r.parent or 'not given'}. ")
                       + f"Close to a child from an earlier round, but not certain. {self.where(r)}. "
                         f"This row is not counted until you decide.",
                       record_ids=[r.id], options=opts)

    def run(self):
        s = self.s
        for t in DERIVED:
            s.execute(delete(t))
        s.flush()
        self.class_copies()
        self.placeholders()
        self.relay_units()
        self.names()
        self.build()
        self.ages()
        self.outliers()
        self.percentiles()
        self.child_rounds()
        self.flags()
        for k, i in self.issues.items():
            if k in self.res:
                i.resolved, i.resolution = True, self.res[k]
        s.add_all(self.issues.values())
        s.flush()


def rebuild(s) -> None:
    Builder(s).run()


def resolve(s, key: str, payload: dict, user_id=None) -> None:
    """Store a coordinator decision and rebuild. Name decisions also relink the row."""
    if key.startswith("name:"):
        r = s.get(Record, int(key.split(":")[1]))
        if payload.get("new"):
            new_child(s, r)
        else:
            r.child_id = payload["child_id"]
        r.link_status = "confirmed"
        for o in s.scalars(select(Record).where(Record.twin_id == r.id)):
            o.child_id = r.child_id
    row = s.get(Resolution, key)
    if row:
        row.payload, row.decided_by, row.decided_at = payload, user_id, dt.datetime.now()
    else:
        s.add(Resolution(key=key, payload=payload, decided_by=user_id))
    s.flush()
    rebuild(s)
    s.commit()


def undo(s, key: str) -> None:
    row = s.get(Resolution, key)
    if row is None:
        return
    if key.startswith("name:"):
        r = s.get(Record, int(key.split(":")[1]))
        r.child_id, r.link_status = None, "review"
    s.delete(row)
    s.flush()
    rebuild(s)
    s.commit()
