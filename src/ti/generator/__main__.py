"""Generate one synthetic school: `python -m ti.generator --school school_a --seed 42`."""

import argparse
import csv
import random
import shutil

from ti import config
from ti.generator import guideline, structured, whatsapp
from ti.generator.profiles import assign_profiles
from ti.generator.roster import COACH, PE_TEACHER, build_roster
from ti.generator.truth import TruthLog
from ti.llm import OllamaClient


def generate(school: str, seed: int, client, data_dir=None) -> dict:
    """Write every source file for one school. Each component draws from its own seeded
    stream, so changing one file's logic does not reshuffle the others."""
    rng = lambda part: random.Random(f"{seed}:{part}")
    data_dir = data_dir or config.DATA_DIR
    out = data_dir / school
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    prog = data_dir / "programme"
    prog.mkdir(parents=True, exist_ok=True)

    roster = build_roster(rng("roster"))
    profiles = assign_profiles(roster, rng("profiles"))
    truth = TruthLog()
    truth.canonical = {c.child_id: (c.first, c.full) for c in roster}
    with open(out / "roster.csv", "w", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=list(roster[0].row()))
        wr.writeheader()
        wr.writerows(c.row() for c in roster)

    with open(out / "staff.csv", "w", newline="") as f:
        wr = csv.writer(f)
        wr.writerow(["role", "name", "note"])
        wr.writerow(["coach", COACH.removeprefix("Coach "), "fictional HRS coach"])
        wr.writerow(["pe_teacher", PE_TEACHER.removesuffix(" (PE)"), "fictional PE teacher"])

    concern_left = {cid: p.concern_budget for cid, p in profiles.items() if p.concern_budget}
    structured.write_attendance(out, roster, profiles, truth, rng("attendance"))
    structured.write_coach_forms(out, roster, profiles, truth, rng("forms"), concern_left)
    structured.write_assessments(out, roster, profiles, truth, rng("assessments"))
    n_msgs = whatsapp.write_chat(out, roster, profiles, truth, client, rng("whatsapp"),
                                 concern_left)
    guideline.write_guideline(prog)
    truth.write(out / "ground_truth.json", roster, profiles)
    return {"school": school, "children": len(roster), "messages": n_msgs,
            "mentions": len(truth.mentions)}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--school", default="school_a")
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()
    client = OllamaClient()
    client.check()
    print(generate(args.school, args.seed, client))


if __name__ == "__main__":
    main()
