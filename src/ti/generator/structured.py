"""Structured sources in the shapes coaches and teachers actually use."""

import csv
import datetime as dt
import random
from pathlib import Path

from ti.generator import names
from ti.generator.profiles import N_WEEKS, Profile, sessions
from ti.generator.roster import COACH, Child
from ti.generator.truth import TruthLog

PRAISE = [
    "{n} was very focused in the sprint drills",
    "{n} improved a lot on the 600m loop",
    "{n} helped the younger ones with warm up",
    "{n} ran really well in the relay",
    "{n} kept good form till the last lap",
]
PARTICIPATION = [
    "{n} did all the drills",
    "{n} took part fully in the relay",
    "{n} finished the full warm up and cool down",
]
CONCERN = [
    "{n} seemed very tired and stopped midway",
    "{n} complained of knee pain after the run",
    "{n} was not interested today and sat out the relay",
    "{n} was breathless early, need to keep an eye",
]
OPENERS = [
    "Good session overall.", "Ground was wet, did shorter drills.", "Hot day, kept it light.",
    "Relay practice today.", "Speed work and stretching.", "", "Mixed session.",
]


def date_str(d: dt.date) -> str:
    return d.strftime("%d-%m-%Y")


def write_attendance(out: Path, roster: list[Child], profiles: dict[str, Profile],
                     truth: TruthLog, rng: random.Random) -> None:
    """One sheet per week kept by the PE teacher: one row per child per session.

    12 sessions x 25 children = 300 rows. A session that was not recorded for a child keeps
    its row with a blank status (the planted missing weeks).
    """
    dates = sessions()
    for w in range(N_WEEKS):
        week = dates[2 * w: 2 * w + 2]
        fname = f"attendance_wk{w + 1}.csv"
        with open(out / fname, "w", newline="") as f:
            wr = csv.writer(f)
            wr.writerow(["Date", "Day", "Student name", "Status"])
            i = 0
            for day in week:
                for c in roster:
                    i += 1
                    mark = profiles[c.child_id].present[day]
                    name = names.surface(c.first, c.surname, rng, rate=0.2, formal=True)
                    status = "" if mark is None else ("P" if mark else "A")
                    wr.writerow([date_str(day), day.strftime("%a"), name, status])
                    truth.mention(fname, f"row:{i}", name, c.child_id)
                    if mark is None:
                        truth.noise("missing_week", c.child_id, fname, f"row:{i}",
                                    day.isoformat())


def _form_mentions(day: dt.date, roster, profiles, rng, concern_left) -> list[tuple]:
    """Pick 3-5 (child, kind) mentions for one session, honouring planted cases."""
    picks: list[tuple] = []
    for c in roster:
        p = profiles[c.child_id]
        if p.conflict_date == day:
            picks.append((c, "praise"))
    present = [c for c in roster if profiles[c.child_id].present.get(day) is True
               and all(c is not x for x, _ in picks)]
    rng.shuffle(present)
    target = rng.randint(3, 5)
    for c in present:
        if len(picks) >= target:
            break
        if concern_left.get(c.child_id, 0) > 0 and rng.random() < 0.7:
            concern_left[c.child_id] -= 1
            picks.append((c, "concern"))
        else:
            picks.append((c, rng.choice(["praise", "participation"])))
    rng.shuffle(picks)
    return picks


def write_coach_forms(out: Path, roster, profiles, truth: TruthLog, rng: random.Random,
                      concern_left: dict[str, int]) -> None:
    """Google Form export, one response per session; notes are free text."""
    fname = "coach_forms.csv"
    with open(out / fname, "w", newline="") as f:
        wr = csv.writer(f)
        wr.writerow(["Timestamp", "Coach name", "Session date", "Group",
                     "Who stood out / any concerns?"])
        for i, day in enumerate(sessions(), 1):
            late = rng.random() < 0.2  # some forms are filled days later
            ts = dt.datetime.combine(day, dt.time(18, rng.randint(5, 55)))
            if late:
                ts += dt.timedelta(days=rng.randint(1, 3), hours=rng.randint(0, 3))
                truth.noise("late_entry", None, fname, f"row:{i}", day.isoformat())
            parts = []
            for c, kind in _form_mentions(day, roster, profiles, rng, concern_left):
                name = names.surface(c.first, c.surname, rng, rate=0.2)
                tmpl = rng.choice({"praise": PRAISE, "participation": PARTICIPATION,
                                   "concern": CONCERN}[kind])
                parts.append(tmpl.format(n=name))
                truth.mention(fname, f"row:{i}", name, c.child_id)
                truth.fact(c.child_id, kind, fname, f"row:{i}", day.isoformat())
                if profiles[c.child_id].conflict_date == day:
                    truth.noise("conflict", c.child_id, fname, f"row:{i}", day.isoformat())
            opener = rng.choice(OPENERS)
            notes = (opener + " " if opener else "") + ". ".join(parts) + "."
            wr.writerow([ts.strftime("%d/%m/%Y %H:%M:%S"), COACH.removeprefix("Coach "),
                         date_str(day), "Class 6 & 7", notes])


def write_assessments(out: Path, roster, profiles, truth: TruthLog, rng: random.Random) -> None:
    """Baseline (week 1) and midline (week 6) fitness tests: 2 rounds x 25 = 50 rows.
    A child not tested at midline keeps a row with blank results."""
    fname = "assessments.csv"
    dates = sessions()
    rounds = [("baseline", dates[1]), ("midline", dates[-1])]
    with open(out / fname, "w", newline="") as f:
        wr = csv.writer(f)
        wr.writerow(["Round", "Date", "Student name", "50m sprint (s)",
                     "Standing broad jump (cm)", "600m run (s)"])
        i = 0
        for rnd, day in rounds:
            for c in roster:
                vals = profiles[c.child_id].baseline if rnd == "baseline" \
                    else profiles[c.child_id].midline
                i += 1
                name = names.surface(c.first, c.surname, rng, rate=0.1, formal=True)
                if vals is None:
                    wr.writerow([rnd, date_str(day), name, "", "", ""])
                    truth.noise("missing_assessment", c.child_id, fname, f"row:{i}",
                                day.isoformat())
                else:
                    wr.writerow([rnd, date_str(day), name, vals["sprint_50m_s"],
                                 vals["broad_jump_cm"], vals["run_600m_s"]])
                truth.mention(fname, f"row:{i}", name, c.child_id)
