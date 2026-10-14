"""A2 ingest: read every source file for one school into scrubbed SourceLines.

Reads only the known source files; ground_truth.json is never opened here.
"""

import csv
from pathlib import Path

from ti.ingest.parsers import (SourceLine, parse_assessments, parse_attendance,
                               parse_coach_forms, parse_guideline, parse_whatsapp)

__all__ = ["SourceLine", "load_roster", "load_school"]


def load_roster(school_dir: Path) -> list[dict]:
    with open(school_dir / "roster.csv", newline="") as f:
        return list(csv.DictReader(f))


def load_school(school_dir: Path) -> list[SourceLine]:
    lines: list[SourceLine] = []
    for path in sorted(school_dir.glob("attendance_wk*.csv")):
        lines += parse_attendance(path)
    lines += parse_coach_forms(school_dir / "coach_forms.csv")
    lines += parse_assessments(school_dir / "assessments.csv")
    lines += parse_whatsapp(school_dir / "whatsapp.txt")
    guideline = school_dir.parent / "programme" / "guideline.md"
    if guideline.exists():
        lines += parse_guideline(guideline)
    return lines
