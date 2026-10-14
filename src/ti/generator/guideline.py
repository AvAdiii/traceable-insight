"""Synthetic programme guideline. Thresholds are placeholders until validated with HRS."""

from pathlib import Path

import yaml

THRESHOLDS = {
    "synthetic": True,
    "note": "Placeholder values written by the team; validate with HRS before real use.",
    "sessions_planned": 12,
    "min_recorded_sessions": 6,
    "require_midline_assessment": True,
    "attendance_rate_min": 0.60,
    "fitness_decline_pct": 8.0,
    "concern_mentions_min": 2,
}

SECTIONS = [
    ("About this document", "SYNTHETIC. This guideline was written by Team HFMD Aur Samose as a "
     "placeholder for the Project Champion programme guideline. Every number below is a plausible "
     "placeholder and must be validated with Hyderabad Runners Society before real use."),
    ("Programme purpose", "Project Champion brings structured running sessions to government "
     "school children so that every child builds fitness, confidence and a habit of exercise."),
    ("Who the programme serves", "Children in classes 6 and 7, aged roughly 11 to 13, in partner "
     "government schools in Hyderabad."),
    ("Roles", "Each school has one HRS coach who runs sessions and one PE teacher who keeps "
     "attendance and runs fitness assessments. A programme coordinator oversees several schools."),
    ("Session frequency", "Two sessions a week, on Tuesday and Friday, for six weeks per cycle: "
     "12 planned sessions."),
    ("Session structure", "Warm up (10 min), drills (15 min), main run or relay (15 min), "
     "cool down and stretching (5 min)."),
    ("Attendance recording", "The PE teacher marks each child P (present) or A (absent) on the "
     "weekly sheet for every session. A blank cell means the session was not recorded."),
    ("Minimum attendance", "A child is expected to attend at least 60% of recorded sessions. "
     "Below 60% the child needs coaching attention."),
    ("Enough information to judge", "A child's progress can only be judged when at least 6 of the "
     "12 sessions have recorded attendance and the midline assessment has been done."),
    ("Coach session form", "After every session the coach fills a short form naming children who "
     "stood out and any concerns. The form is not a register and does not replace attendance."),
    ("Fitness assessments", "Three tests: 50m sprint, standing broad jump and 600m run. Baseline "
     "in week 1 and midline in week 6."),
    ("Fitness decline", "If a child's 50m sprint or 600m run time at midline is more than 8% "
     "slower than baseline, the child needs coaching attention."),
    ("Expected improvement", "Most children improve by 1 to 5% between baseline and midline. "
     "No improvement on its own is not a concern."),
    ("Repeated concerns", "If the coach or teacher raises a concern about the same child two or "
     "more times in a cycle, the child needs coaching attention."),
    ("What counts as a concern", "Fatigue that stops participation, pain or injury complaints, "
     "breathlessness, or repeated withdrawal from activities."),
    ("Injuries", "Any injury complaint is recorded and the child rests until the coach clears "
     "them. Pain that repeats is escalated to the coordinator."),
    ("Conflicting records", "If two records about a child disagree, for example the coach reports "
     "a child ran on a day the attendance sheet marks them absent, the coordinator checks both "
     "sources before acting."),
    ("WhatsApp group", "Coaches, teachers and the coordinator use one WhatsApp group per school for "
     "updates. Messages are informal and do not replace the attendance sheet."),
    ("Names", "Use the child's name as it appears on the school roster when possible."),
    ("Privacy", "Do not share children's phone numbers, photos or addresses outside the programme."),
    ("Photos and media", "Photos are shared only in the school group and never with names attached."),
    ("Heat and rain", "On very hot or wet days the coach shortens the session and avoids the 600m "
     "loop. A shortened session still counts as a session."),
    ("Hydration", "Every child carries water. Coaches pause for water every 15 minutes."),
    ("Girls' participation", "Coaches make sure girls get equal turns in relays and drills."),
    ("Children who need attention", "The coordinator decides with the coach what extra support a "
     "child receives: extra encouragement, adjusted drills, or a talk with the PE teacher."),
    ("No ranking", "Children are never ranked or scored against each other. The aim is each "
     "child's own progress."),
    ("Coach handover", "When a coach changes, the outgoing coach writes a short note on each child "
     "who needs attention."),
    ("Midline review", "After the midline assessment the coordinator reviews every child with the "
     "coach and PE teacher."),
    ("End of cycle", "At the end of six weeks each school gets a short summary of attendance and "
     "fitness change."),
    ("Changes to this guideline", "Thresholds may change after review with HRS. The current values "
     "are synthetic placeholders."),
]


def write_guideline(out: Path) -> None:
    lines = ["# Project Champion Programme Guideline (SYNTHETIC)", ""]
    for i, (title, body) in enumerate(SECTIONS, 1):
        lines += [f"## {i}. {title}", "", body, ""]
    (out / "guideline.md").write_text("\n".join(lines))
    (out / "thresholds.yaml").write_text(yaml.safe_dump(THRESHOLDS, sort_keys=False))
