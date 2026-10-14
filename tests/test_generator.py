import csv
import datetime as dt
import json
import random
from collections import Counter

import pytest

from ti.generator.__main__ import generate
from ti.generator.profiles import assign_profiles, sessions
from ti.generator.roster import build_roster
from ti.generator.whatsapp import Draft, rewrite
from ti.llm import FakeClient


def truth(school_dir):
    return json.loads((school_dir / "ground_truth.json").read_text())


def test_roster_has_25_and_one_shared_first_name():
    roster = build_roster(random.Random(1))
    assert len(roster) == 25
    firsts = Counter(c.first for c in roster)
    assert firsts["Ravi"] == 2
    assert all(n == 1 for f, n in firsts.items() if f != "Ravi")


def test_planted_counts_are_exact():
    roster = build_roster(random.Random(3))
    prof = assign_profiles(roster, random.Random(4))
    counts = Counter(p.condition for p in prof.values())
    assert counts == {"conflict": 4, "gap": 4, "needs_attention": 5, "on_track": 12}


def test_same_seed_same_files(tmp_path, fake_llm):
    generate("s", 9, fake_llm, data_dir=tmp_path / "a")
    generate("s", 9, FakeClient(fn=fake_llm.fn), data_dir=tmp_path / "b")
    for f in sorted((tmp_path / "a" / "s").iterdir()):
        assert f.read_bytes() == (tmp_path / "b" / "s" / f.name).read_bytes(), f.name


def test_conflict_child_praised_on_a_day_marked_absent(school_dir):
    t = truth(school_dir)
    for conflict in t["planted_conflicts"]:
        day = dt.date.fromisoformat(conflict["date"])
        form_facts = [f for f in t["planted_facts"] if f["child_id"] == conflict["child_id"]
                      and f["file"] == "coach_forms.csv" and f["date"] == conflict["date"]]
        assert form_facts
        week = sessions().index(day) // 2 + 1
        with open(school_dir / f"attendance_wk{week}.csv") as f:
            rows = list(csv.DictReader(f))
        refs = {m["ref"] for m in t["mentions"] if m["file"] == f"attendance_wk{week}.csv"
                and m["child_id"] == conflict["child_id"]}
        marks = [rows[int(r.split(":")[1]) - 1] for r in refs]
        assert any(r["Date"] == day.strftime("%d-%m-%Y") and r["Status"] == "A" for r in marks)


def test_volumes_match_the_plan(school_dir):
    att = sum(len(list(csv.DictReader(open(p)))) for p in school_dir.glob("attendance_wk*.csv"))
    assert att == 300
    with open(school_dir / "assessments.csv") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 50
    assert sum(1 for r in rows if r["Round"] == "midline" and not r["600m run (s)"]) == 2
    with open(school_dir / "coach_forms.csv") as f:
        assert len(list(csv.DictReader(f))) == 12
    staff = (school_dir / "staff.csv").read_text()
    assert "coach" in staff and "pe_teacher" in staff


def test_noise_is_logged(school_dir):
    noise = truth(school_dir)["noise"]
    assert noise["missing_weeks"] and noise["missing_assessments"]
    assert len(noise["contradictory_reports"]) == 4
    assert noise["name_variants"]
    assert "late_entries" in noise


def test_demo_variants_for_ravi_kumar_are_planted(school_dir):
    t = truth(school_dir)
    rk = next(c["child_id"] for c in t["children"] if c["first"] == "Ravi" and c["surname"] == "Kumar")
    surfaces = {m["surface"] for m in t["mentions"] if m["child_id"] == rk}
    assert {"Ravi K", "Ravikumar"} <= surfaces


def test_chat_volume_pii_and_ambiguous_ravi(school_dir):
    text = (school_dir / "whatsapp.txt").read_text()
    t = truth(school_dir)
    n_msgs = sum(1 for line in text.splitlines() if " - " in line and ": " in line.split(" - ", 1)[1])
    assert 180 <= n_msgs <= 240
    assert "+91 90000" in text and "<Media omitted>" in text and "https://" in text
    amb = [m for m in t["mentions"] if m["child_id"] == "ambiguous"]
    assert len(amb) == 2 and all(m["surface"] == "ravi" for m in amb)


def test_variant_share_near_twenty_percent(school_dir):
    t = truth(school_dir)
    kids = {c["child_id"]: c for c in t["children"]}
    named = [m for m in t["mentions"] if m["child_id"] != "ambiguous"]
    plain = sum(m["surface"] in (kids[m["child_id"]]["first"],
                                 f'{kids[m["child_id"]]["first"]} {kids[m["child_id"]]["surname"]}')
                for m in named)
    assert 0.12 <= 1 - plain / len(named) <= 0.3


def test_rewrite_keeps_misspelt_name_verbatim():
    roster = build_roster(random.Random(1))
    d = Draft(dt.datetime(2026, 7, 7, 9), "Coach", meaning="Jyothii did the full session.",
              mentions=[("Jyothii", "A01")])
    client = FakeClient(responses=[{"text": "aaj @1 ne poora session kiya"}])
    assert rewrite(d, client, roster) == "aaj Jyothii ne poora session kiya"


def test_rewrite_retries_then_fails():
    roster = build_roster(random.Random(1))
    d = Draft(dt.datetime(2026, 7, 7, 9), "Coach", meaning="Ravi K ran well.",
              mentions=[("Ravi K", "A01")])
    client = FakeClient(responses=[{"text": "Ravi ran"}] * 3)
    with pytest.raises(RuntimeError):
        rewrite(d, client, roster)
    assert len(client.prompts) == 3
