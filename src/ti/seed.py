"""Demo workspace: `uv run python -m ti.seed [--fresh]`.

Generates the synthetic workbooks if missing, creates demo users, schools with coaches, the three
rounds, uploads every workbook through the real pipeline, and adds sports-meet events (one past
meet with results, upcoming meets with to-dos).

Demo logins (password "champion"):
  manager@champion.demo     programme manager, all schools
  supervisor@champion.demo  supervisor PT, four schools
  trainer@champion.demo     PT trainer, one school
"""

import argparse
import datetime as dt
import json

from sqlalchemy import select

from ti import auth, config, db, pipeline, shortlist
from ti.db import Event, EventItem, Result, Round, School, Selection, Todo, User
from ti.generator import ROUNDS, SCHOOLS, generate

PEOPLE = [
    ("manager@champion.demo", "Anita Rao", "manager"),
    ("supervisor@champion.demo", "Ramesh Goud", "supervisor"),
    ("supervisor2@champion.demo", "Farida Begum", "supervisor"),
    ("trainer@champion.demo", "Kiran Kumar", "trainer"),
    ("trainer2@champion.demo", "Swapna Reddy", "trainer"),
    ("trainer3@champion.demo", "Imran Khan", "trainer"),
    ("trainer4@champion.demo", "Lavanya Devi", "trainer"),
    ("trainer5@champion.demo", "Suresh Naik", "trainer"),
]


def seed(fresh: bool = False, today: dt.date | None = None) -> None:
    today = today or dt.date.today()
    if fresh and config.DATABASE_URL.startswith("sqlite:///"):
        p = config.VAR_DIR / "ti.db"
        for suffix in ("", "-wal", "-shm"):
            q = p.with_name(p.name + suffix)
            if q.exists():
                q.unlink()
        db.use(config.DATABASE_URL)
    elif fresh:
        db.Base.metadata.drop_all(db.engine())
    db.create_all()
    if not (config.DEMO_DIR / "ground_truth.json").exists():
        generate(config.DEMO_DIR)
    truth = json.loads((config.DEMO_DIR / "ground_truth.json").read_text())
    s = db.session()
    if s.scalar(select(User).limit(1)):
        print("already seeded; use --fresh to rebuild")
        return
    users = []
    for email, name, role in PEOPLE:
        u = User(email=email, name=name, role=role, password_hash=auth.hash_password("champion"))
        s.add(u)
        users.append(u)
    s.flush()
    trainers = [u for u in users if u.role == "trainer"]
    sups = [u for u in users if u.role == "supervisor"]
    for i, (name, short, area, *_rest) in enumerate(SCHOOLS):
        s.add(School(id=pipeline.slug(name), name=name, short=short, area=area,
                     trainer_id=trainers[i % len(trainers)].id, supervisor_id=sups[i // 4].id,
                     hue=[211, 142, 28, 268, 340, 190, 52, 4][i]))
    rounds = {}
    for kind, label, date in ROUNDS:
        r = Round(label=label, kind=kind, test_date=date)
        s.add(r)
        rounds[kind] = r
    s.flush()
    for fname, meta in truth["files"].items():
        data = (config.DEMO_DIR / fname).read_bytes()
        up = pipeline.ingest_upload(s, data, fname, rounds[meta["kind"]].id,
                                    trainers[0].id if meta["kind"] != "baseline" else users[0].id)
        print(f"uploaded {fname}: {up.summary}")
    _events(s, today, users[0].id)
    s.commit()
    print("seeded. logins: manager@champion.demo / champion")


def _events(s, today: dt.date, uid: int) -> None:
    def d(days):
        return today + dt.timedelta(days=days)

    past = Event(title="Zonal Athletics Meet", kind="meet", level="zonal", start_date=d(-24),
                 venue="GHMC Sports Complex, Yousufguda", start_time="08:00",
                 notes="Under-12 and Under-14 track and field.", created_by=uid)
    trials = Event(title="District selection trials", kind="trial", level="district",
                   start_date=d(12), venue="Gachibowli Stadium (warm-up track)", start_time="07:30",
                   notes="Bring birth certificates for age verification.", created_by=uid)
    annual = Event(title="Project Champion Annual Meet", kind="meet", level="annual",
                   start_date=d(33), end_date=d(34), venue="LB Stadium, Basheerbagh",
                   start_time="08:00",
                   notes="About 1 in 7 children are shortlisted through the test battery.",
                   created_by=uid)
    state = Event(title="Telangana State School Games", kind="meet", level="state",
                  start_date=d(68), end_date=d(70), venue="Hanamkonda", created_by=uid)
    endline = Event(title="Endline assessment window", kind="assessment", level="school",
                    start_date=d(95), end_date=d(105), venue="All schools", created_by=uid)
    s.add_all([past, trials, annual, state, endline])
    s.flush()
    items = {
        past.id: [("60 m sprint", "sprint", "Boys", 9, 11, 3), ("60 m sprint", "sprint", "Girls", 9, 11, 3),
                  ("Long jump", "long_jump", "Girls", 11, 13, 2), ("Ball throw", "throw", "Boys", 11, 13, 2)],
        trials.id: [("100 m sprint", "sprint", "Boys", 12, 14, 4), ("100 m sprint", "sprint", "Girls", 12, 14, 4),
                    ("600 m run", "endurance", "Girls", 10, 12, 3), ("Shot put", "throw", "Boys", 12, 14, 3)],
        annual.id: [("50 m sprint", "sprint", "Any", 6, 8, 6), ("4×100 m relay", "relay", "Girls", 10, 12, 4),
                    ("4×100 m relay", "relay", "Boys", 10, 12, 4), ("Standing broad jump", "long_jump", "Any", 8, 10, 6),
                    ("Medicine ball throw", "throw", "Girls", 12, 15, 4), ("All-round champion", "all_round", "Any", 6, 15, 10)],
        state.id: [("Long jump", "long_jump", "Boys", 13, 15, 2), ("800 m run", "endurance", "Girls", 13, 15, 2)],
    }
    for eid, rows in items.items():
        for name, disc, g, lo, hi, slots in rows:
            s.add(EventItem(event_id=eid, name=name, discipline=disc, gender=g, age_min=lo,
                            age_max=hi, slots=slots, reserves=2 if slots < 6 else 3))
    s.flush()
    # The past meet: picks confirmed, results recorded.
    for item in s.scalars(select(EventItem).where(EventItem.event_id == past.id)):
        picks = shortlist.suggest(s, item, None)["selected"]
        for rank, p in enumerate(picks, start=1):
            s.add(Selection(item_id=item.id, child_id=p["child_id"], status="selected", rank=rank,
                            reason={"summary": p["summary"]}))
            if rank <= 3:
                s.add(Result(item_id=item.id, child_id=p["child_id"], position=rank,
                             mark={"sprint": f"{8.9 + rank * 0.3:.1f} s"}.get(item.discipline,
                                                                             f"{3.4 - rank * 0.2:.2f} m"),
                             note="Gold" if rank == 1 else "Silver" if rank == 2 else "Bronze"))
    # Trials: two items already picked.
    for item in list(s.scalars(select(EventItem).where(EventItem.event_id == trials.id)))[:2]:
        sug = shortlist.suggest(s, item, None)
        for rank, p in enumerate(sug["selected"], start=1):
            s.add(Selection(item_id=item.id, child_id=p["child_id"], status="selected", rank=rank,
                            reason={"summary": p["summary"]}))
        for rank, p in enumerate(sug["reserves"], start=1):
            s.add(Selection(item_id=item.id, child_id=p["child_id"], status="reserve", rank=rank,
                            reason={"summary": p["summary"]}))
    s.add_all([
        Todo(event_id=trials.id, text="Collect birth certificates from selected children", due_date=d(8)),
        Todo(event_id=trials.id, text="Parent consent forms signed", due_date=d(9)),
        Todo(event_id=trials.id, text="Book school bus for 7:00 am pickup", due_date=d(10), done=True),
        Todo(event_id=annual.id, text="Finalise shortlist with supervisors", due_date=d(20)),
        Todo(event_id=annual.id, text="Order participant T-shirts (sizes from heights)", due_date=d(22)),
        Todo(event_id=annual.id, text="Confirm LB Stadium booking", due_date=d(5), done=True),
        Todo(text="Remind Bapuji Nagar trainer: shuttle times look like placeholders", due_date=d(2)),
    ])


if __name__ == "__main__":  # pragma: no cover
    ap = argparse.ArgumentParser()
    ap.add_argument("--fresh", action="store_true")
    seed(ap.parse_args().fresh)
