"""Parsers: each source file becomes SourceLines with a stable ref (row:N, msg:N, sec:N)."""

import csv
import datetime as dt
import re
from dataclasses import dataclass, field
from pathlib import Path

from ti.ingest.pii import scrub


@dataclass
class SourceLine:
    source_file: str
    ref: str
    text: str
    kind: str                     # attendance | coach_form | assessment | whatsapp | guideline
    meta: dict = field(default_factory=dict)


def _date(s: str) -> str:
    """dd-mm-yyyy or dd/mm/yyyy or dd/mm/yy -> ISO date."""
    s = s.strip().replace("/", "-")
    fmt = "%d-%m-%Y" if len(s.split("-")[-1]) == 4 else "%d-%m-%y"
    return dt.datetime.strptime(s, fmt).date().isoformat()


def parse_attendance(path: Path) -> list[SourceLine]:
    """Weekly sheet, one row per child per session: Date, Day, Student name, Status."""
    with open(path, newline="") as f:
        rows = list(csv.reader(f))
    header, body = rows[0], rows[1:]
    out = []
    for i, row in enumerate(body, 1):
        rec = dict(zip(header, row))
        date = _date(rec["Date"])
        mark = rec["Status"].strip().upper() or None
        out.append(SourceLine(path.name, f"row:{i}", ",".join(row), "attendance",
                              {"name": rec["Student name"].strip(), "date": date,
                               "marks": {date: mark}, "header": ",".join(header)}))
    return out


def parse_coach_forms(path: Path) -> list[SourceLine]:
    out = []
    with open(path, newline="") as f:
        for i, row in enumerate(csv.DictReader(f), 1):
            notes = scrub(row["Who stood out / any concerns?"]) or ""
            out.append(SourceLine(path.name, f"row:{i}", notes, "coach_form", {
                "date": _date(row["Session date"]),
                "submitted": row["Timestamp"], "coach": row["Coach name"], "group": row["Group"]}))
    return out


def parse_assessments(path: Path) -> list[SourceLine]:
    metrics = {"50m sprint (s)": "sprint_50m_s", "Standing broad jump (cm)": "broad_jump_cm",
               "600m run (s)": "run_600m_s"}
    with open(path, newline="") as f:
        rows = list(csv.reader(f))
    header = rows[0]
    out = []
    for i, row in enumerate(rows[1:], 1):
        rec = dict(zip(header, row))
        out.append(SourceLine(path.name, f"row:{i}", ",".join(row), "assessment", {
            "round": rec["Round"], "date": _date(rec["Date"]), "name": rec["Student name"].strip(),
            "header": ",".join(header),
            **{k: (float(rec[col]) if rec[col].strip() else None)
               for col, k in metrics.items()}}))
    return out


WA_LINE = re.compile(r"^(\d{2}/\d{2}/\d{2}), (\d{1,2}:\d{2}\s?[ap]m) - (.*)$")


def parse_whatsapp(path: Path) -> list[SourceLine]:
    """Android export. Continuation lines join the previous message; system lines are skipped.
    msg:N counts every sender message in file order, including ones the scrub drops."""
    msgs: list[dict] = []
    for raw in path.read_text().splitlines():
        m = WA_LINE.match(raw)
        if m:
            date, time, rest = m.groups()
            if ": " not in rest:
                continue  # system line, e.g. encryption notice
            sender, body = rest.split(": ", 1)
            msgs.append({"date": _date(date), "time": time, "sender": sender, "body": body})
        elif msgs:
            msgs[-1]["body"] += "\n" + raw
    out = []
    for i, m in enumerate(msgs, 1):
        body = scrub(m["body"])
        if body is None:
            continue
        out.append(SourceLine(path.name, f"msg:{i}", body, "whatsapp", {
            "date": m["date"], "time": m["time"], "sender": scrub(m["sender"])}))
    return out


def parse_guideline(path: Path) -> list[SourceLine]:
    """Markdown guideline split on '## ' headings, one chunk per section."""
    out = []
    for block in path.read_text().split("\n## ")[1:]:
        title, _, body = block.partition("\n")
        num, _, name = title.partition(". ")
        out.append(SourceLine(path.name, f"sec:{num}", body.strip(), "guideline",
                              {"title": name.strip()}))
    return out
