"""Store schema (SQLAlchemy 2). SQLite locally, Postgres when hosted.

Persistent tables hold what people entered or decided: users, schools, rounds, uploads, records
(one per spreadsheet row, with its raw cells), children (identity registry), resolutions,
events and everything under them, settings, audit log.

Derived tables are rebuilt by ti.pipeline.rebuild() after every upload or decision:
measurements, child_rounds, flags, issues.
"""

import datetime as dt
from typing import Any

from sqlalchemy import (JSON, Boolean, Date, DateTime, Float, ForeignKey, Integer, String,
                        Text, UniqueConstraint, create_engine, event)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

from ti import config


def now() -> dt.datetime:
    return dt.datetime.now(dt.UTC).replace(tzinfo=None)


class Base(DeclarativeBase):
    type_annotation_map = {dict[str, Any]: JSON, list[Any]: JSON}


# ---------------------------------------------------------------- persistent

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(200), unique=True)
    name: Mapped[str] = mapped_column(String(120))
    role: Mapped[str] = mapped_column(String(20))          # manager | supervisor | trainer
    password_hash: Mapped[str] = mapped_column(String(300))
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=now)


class School(Base):
    __tablename__ = "schools"
    id: Mapped[str] = mapped_column(String(60), primary_key=True)     # slug
    name: Mapped[str] = mapped_column(String(200), unique=True)       # as written in sheets
    short: Mapped[str] = mapped_column(String(60))
    area: Mapped[str] = mapped_column(String(120), default="")
    trainer_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    supervisor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    hue: Mapped[int] = mapped_column(Integer, default=210)            # UI accent


class Round(Base):
    __tablename__ = "rounds"
    id: Mapped[int] = mapped_column(primary_key=True)
    label: Mapped[str] = mapped_column(String(80), unique=True)       # "Baseline 2025-26"
    kind: Mapped[str] = mapped_column(String(20))                     # baseline|midline|endline|custom
    test_date: Mapped[dt.date] = mapped_column(Date)


class Upload(Base):
    __tablename__ = "uploads"
    id: Mapped[int] = mapped_column(primary_key=True)
    filename: Mapped[str] = mapped_column(String(300))
    sha256: Mapped[str] = mapped_column(String(64))
    size: Mapped[int] = mapped_column(Integer)
    stored_path: Mapped[str] = mapped_column(String(500))
    round_id: Mapped[int] = mapped_column(ForeignKey("rounds.id"))
    uploaded_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    uploaded_at: Mapped[dt.datetime] = mapped_column(DateTime, default=now)
    status: Mapped[str] = mapped_column(String(20), default="accepted")   # accepted | refused
    summary: Mapped[dict[str, Any]] = mapped_column(default=dict)
    sheets: Mapped[dict[str, Any]] = mapped_column(default=dict)   # sheet -> {header row, column map}


class Record(Base):
    """One spreadsheet row as it was read. cells: field -> {col, raw}."""
    __tablename__ = "records"
    id: Mapped[int] = mapped_column(primary_key=True)
    upload_id: Mapped[int] = mapped_column(ForeignKey("uploads.id", ondelete="CASCADE"), index=True)
    sheet: Mapped[str] = mapped_column(String(120))
    row: Mapped[int] = mapped_column(Integer)
    preferred: Mapped[bool] = mapped_column(Boolean, default=True)   # from the sheet that counts
    twin_id: Mapped[int | None] = mapped_column(Integer)              # same row in the other sheet
    school_id: Mapped[str | None] = mapped_column(ForeignKey("schools.id"))
    klass: Mapped[str] = mapped_column(String(20), default="")
    name: Mapped[str] = mapped_column(String(200), default="")
    parent: Mapped[str] = mapped_column(String(200), default="")
    dob: Mapped[dt.date | None] = mapped_column(Date)
    gender: Mapped[str] = mapped_column(String(10), default="")
    cells: Mapped[dict[str, Any]] = mapped_column(default=dict)
    raw_row: Mapped[list[Any]] = mapped_column(default=list)
    child_id: Mapped[str | None] = mapped_column(ForeignKey("children.id"), index=True)
    link_status: Mapped[str] = mapped_column(String(20), default="new")  # exact|fuzzy|new|review|confirmed
    link_score: Mapped[float | None] = mapped_column(Float)
    link_candidates: Mapped[list[Any]] = mapped_column(default=list)


class Child(Base):
    __tablename__ = "children"
    id: Mapped[str] = mapped_column(String(12), primary_key=True)
    school_id: Mapped[str] = mapped_column(ForeignKey("schools.id"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    parent: Mapped[str] = mapped_column(String(200), default="")
    dob: Mapped[dt.date | None] = mapped_column(Date)
    gender: Mapped[str] = mapped_column(String(10), default="")
    klass: Mapped[str] = mapped_column(String(20), default="")
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=now)


class Resolution(Base):
    """A coordinator decision on an Inbox item. key identifies what it answers."""
    __tablename__ = "resolutions"
    key: Mapped[str] = mapped_column(String(200), primary_key=True)
    payload: Mapped[dict[str, Any]] = mapped_column(default=dict)
    decided_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    decided_at: Mapped[dt.datetime] = mapped_column(DateTime, default=now)


class Event(Base):
    __tablename__ = "events"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    kind: Mapped[str] = mapped_column(String(20), default="meet")   # meet|trial|assessment|session|other
    level: Mapped[str] = mapped_column(String(20), default="school")  # school|zonal|district|state|national|annual
    start_date: Mapped[dt.date] = mapped_column(Date)
    end_date: Mapped[dt.date | None] = mapped_column(Date)
    start_time: Mapped[str] = mapped_column(String(10), default="")
    venue: Mapped[str] = mapped_column(String(200), default="")
    notes: Mapped[str] = mapped_column(Text, default="")
    school_ids: Mapped[list[Any]] = mapped_column(default=list)   # empty = all schools
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=now)


class EventItem(Base):
    """One race or field event inside a meet, e.g. 60 m sprint, U-12 girls, 3 places."""
    __tablename__ = "event_items"
    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    discipline: Mapped[str] = mapped_column(String(30))   # see ti.shortlist.DISCIPLINES
    gender: Mapped[str] = mapped_column(String(10), default="Any")
    age_min: Mapped[int | None] = mapped_column(Integer)
    age_max: Mapped[int | None] = mapped_column(Integer)
    slots: Mapped[int] = mapped_column(Integer, default=3)
    reserves: Mapped[int] = mapped_column(Integer, default=2)


class Selection(Base):
    __tablename__ = "selections"
    __table_args__ = (UniqueConstraint("item_id", "child_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("event_items.id", ondelete="CASCADE"), index=True)
    child_id: Mapped[str] = mapped_column(ForeignKey("children.id"))
    status: Mapped[str] = mapped_column(String(12), default="selected")   # selected | reserve
    rank: Mapped[int] = mapped_column(Integer, default=0)
    reason: Mapped[dict[str, Any]] = mapped_column(default=dict)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=now)


class Result(Base):
    __tablename__ = "results"
    __table_args__ = (UniqueConstraint("item_id", "child_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("event_items.id", ondelete="CASCADE"), index=True)
    child_id: Mapped[str] = mapped_column(ForeignKey("children.id"), index=True)
    position: Mapped[int | None] = mapped_column(Integer)
    mark: Mapped[str] = mapped_column(String(40), default="")
    note: Mapped[str] = mapped_column(String(300), default="")
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=now)


class Todo(Base):
    __tablename__ = "todos"
    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[int | None] = mapped_column(ForeignKey("events.id", ondelete="CASCADE"))
    text: Mapped[str] = mapped_column(String(300))
    due_date: Mapped[dt.date | None] = mapped_column(Date)
    done: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=now)


class Setting(Base):
    __tablename__ = "settings"
    key: Mapped[str] = mapped_column(String(60), primary_key=True)
    value: Mapped[dict[str, Any]] = mapped_column(default=dict)


class Audit(Base):
    __tablename__ = "audit_log"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(60))
    detail: Mapped[dict[str, Any]] = mapped_column(default=dict)
    at: Mapped[dt.datetime] = mapped_column(DateTime, default=now)


# ---------------------------------------------------------------- derived

class Measurement(Base):
    """One test value for one child in one round, with the cell it came from."""
    __tablename__ = "measurements"
    id: Mapped[int] = mapped_column(primary_key=True)
    child_id: Mapped[str] = mapped_column(ForeignKey("children.id"), index=True)
    round_id: Mapped[int] = mapped_column(ForeignKey("rounds.id"))
    field: Mapped[str] = mapped_column(String(20))
    value: Mapped[float | None] = mapped_column(Float)
    raw: Mapped[str] = mapped_column(String(80), default="")
    status: Mapped[str] = mapped_column(String(12))   # ok|repaired|corrected|accepted|suspect|disputed|missing
    note: Mapped[str] = mapped_column(String(300), default="")
    record_id: Mapped[int] = mapped_column(ForeignKey("records.id"))
    cell: Mapped[str] = mapped_column(String(12), default="")
    percentile: Mapped[float | None] = mapped_column(Float)
    pool: Mapped[str] = mapped_column(String(60), default="")


class ChildRound(Base):
    __tablename__ = "child_rounds"
    id: Mapped[int] = mapped_column(primary_key=True)
    child_id: Mapped[str] = mapped_column(ForeignKey("children.id"), index=True)
    round_id: Mapped[int] = mapped_column(ForeignKey("rounds.id"))
    school_id: Mapped[str] = mapped_column(ForeignKey("schools.id"))
    klass: Mapped[str] = mapped_column(String(20), default="")
    age: Mapped[float | None] = mapped_column(Float)
    composite: Mapped[float | None] = mapped_column(Float)
    n_tests: Mapped[int] = mapped_column(Integer, default=0)


class Flag(Base):
    __tablename__ = "flags"
    id: Mapped[int] = mapped_column(primary_key=True)
    child_id: Mapped[str] = mapped_column(ForeignKey("children.id"), index=True)
    kind: Mapped[str] = mapped_column(String(20))   # top|improved|push|declining|missing
    text: Mapped[str] = mapped_column(String(300))
    weight: Mapped[float] = mapped_column(Float, default=0)   # for ordering within a kind
    evidence: Mapped[list[Any]] = mapped_column(default=list)   # measurement ids


class Issue(Base):
    """An Inbox item about the data, not about the child's performance."""
    __tablename__ = "issues"
    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(200), index=True)   # matches Resolution.key
    kind: Mapped[str] = mapped_column(String(30))
    severity: Mapped[str] = mapped_column(String(10))   # high | medium | low
    school_id: Mapped[str | None] = mapped_column(ForeignKey("schools.id"))
    upload_id: Mapped[int | None] = mapped_column(ForeignKey("uploads.id"))
    child_id: Mapped[str | None] = mapped_column(ForeignKey("children.id"))
    field: Mapped[str] = mapped_column(String(20), default="")
    title: Mapped[str] = mapped_column(String(300))
    detail: Mapped[str] = mapped_column(Text, default="")
    record_ids: Mapped[list[Any]] = mapped_column(default=list)
    options: Mapped[list[Any]] = mapped_column(default=list)    # [{id, label, payload}]
    count: Mapped[int] = mapped_column(Integer, default=1)
    resolved: Mapped[bool] = mapped_column(Boolean, default=False)
    resolution: Mapped[dict[str, Any]] = mapped_column(default=dict)


DERIVED = [Measurement, ChildRound, Flag, Issue]

_engine = None
_Session = None


def engine():
    global _engine, _Session
    if _engine is None:
        url = config.DATABASE_URL
        if url.startswith("sqlite:///"):
            config.VAR_DIR.mkdir(parents=True, exist_ok=True)
        _engine = create_engine(url, future=True, pool_pre_ping=True,
                                connect_args={"check_same_thread": False} if url.startswith("sqlite") else {})
        if url.startswith("sqlite"):
            @event.listens_for(_engine, "connect")
            def _fk(dbapi_conn, _):
                dbapi_conn.execute("PRAGMA foreign_keys=ON")
                dbapi_conn.execute("PRAGMA journal_mode=WAL")
        _Session = sessionmaker(_engine, expire_on_commit=False)
    return _engine


def use(url: str) -> None:
    """Point the store somewhere else (tests)."""
    global _engine, _Session
    config.DATABASE_URL = url
    _engine = _Session = None
    engine()


def session():
    engine()
    return _Session()


def create_all() -> None:
    Base.metadata.create_all(engine())
