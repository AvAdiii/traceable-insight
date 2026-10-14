"""Ground-truth log. Written by the generator, read only by ti.score, never by the pipeline."""

import json
from pathlib import Path


class TruthLog:
    def __init__(self):
        self.mentions: list[dict] = []
        self.planted_facts: list[dict] = []
        self.noise_log: list[dict] = []
        self.canonical: dict[str, tuple[str, str]] = {}

    def mention(self, file: str, ref: str, surface: str, child_id: str) -> None:
        """child_id is a roster id, or "ambiguous" for a mention that must go to review.
        A mention is a variant when it is neither the first name nor the full name."""
        variant = child_id == "ambiguous"
        if child_id in self.canonical:
            first, full = self.canonical[child_id]
            variant = surface not in (first, full)
        self.mentions.append({"file": file, "ref": ref, "surface": surface,
                              "child_id": child_id, "variant": variant})

    def fact(self, child_id: str, kind: str, file: str, ref: str, date: str = "") -> None:
        self.planted_facts.append(
            {"child_id": child_id, "kind": kind, "file": file, "ref": ref, "date": date})

    def noise(self, kind: str, child_id: str | None, file: str, ref: str, date: str = "") -> None:
        """Deliberate mess: missing_week, missing_assessment, late_entry, conflict."""
        self.noise_log.append({"kind": kind, "child_id": child_id, "file": file, "ref": ref,
                               "date": date})

    def write(self, path: Path, roster, profiles) -> None:
        states = {"conflict": "Conflict to review", "gap": "Not enough information",
                  "needs_attention": "Needs attention", "on_track": "On track"}
        children = []
        conflicts, gaps = [], []
        for c in roster:
            p = profiles[c.child_id]
            children.append({**c.row(), "condition": p.condition, "kind": p.kind,
                             "expected_state": states[p.condition]})
            if p.condition == "conflict":
                conflicts.append({"child_id": c.child_id, "date": p.conflict_date.isoformat(),
                                  "rule": "coach form reports participation; attendance marks absent"})
            if p.condition == "gap":
                gaps.append({"child_id": c.child_id, "kind": p.kind})
        doc = {
            "note": "SYNTHETIC ground truth. Used only by ti.score; the pipeline never reads it.",
            "children": children,
            "planted_conflicts": conflicts,
            "planted_gaps": gaps,
            "mentions": self.mentions,
            "planted_facts": self.planted_facts,
            "noise": {
                "name_variants": [m for m in self.mentions if m.get("variant")],
                "missing_weeks": [n for n in self.noise_log if n["kind"] == "missing_week"],
                "missing_assessments": [n for n in self.noise_log
                                        if n["kind"] == "missing_assessment"],
                "late_entries": [n for n in self.noise_log if n["kind"] == "late_entry"],
                "contradictory_reports": [n for n in self.noise_log if n["kind"] == "conflict"],
            },
        }
        path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n")
