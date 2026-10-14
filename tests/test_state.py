import json

from ti.state import ATTENTION, CONFLICT, GAP, ON_TRACK, evaluate

TH = {"sessions_planned": 12, "min_recorded_sessions": 6, "require_midline_assessment": True,
      "attendance_rate_min": 0.6, "fitness_decline_pct": 8.0, "concern_mentions_min": 2}
DATES = [f"2026-07-{d:02d}" for d in range(7, 19)]
_id = iter(range(1, 10_000))


def att(date, mark):
    return {"fact_id": next(_id), "type": "attendance", "date": date, "line_kind": "attendance",
            "value": json.dumps({"mark": mark})}


def assess(rnd, run=180, sprint=9.0):
    return {"fact_id": next(_id), "type": "assessment", "date": "2026-07-07",
            "line_kind": "assessment",
            "value": json.dumps({"round": rnd, "run_600m_s": run, "sprint_50m_s": sprint,
                                 "broad_jump_cm": 150})}


def note(date, ftype, kind="coach_form"):
    return {"fact_id": next(_id), "type": ftype, "date": date, "line_kind": kind, "value": "{}"}


def healthy(absent=()):
    return [att(d, "A" if d in absent else "P") for d in DATES] + \
        [assess("baseline"), assess("midline", run=175)]


def test_on_track():
    assert evaluate(healthy(), TH).state == ON_TRACK


def test_low_attendance_needs_attention():
    st = evaluate(healthy(absent=DATES[:6]), TH)
    assert st.state == ATTENTION and "6 of 12" in st.reason and len(st.evidence) == 6


def test_fitness_decline_needs_attention():
    facts = [att(d, "P") for d in DATES] + [assess("baseline", run=170),
                                            assess("midline", run=190)]
    st = evaluate(facts, TH)
    assert st.state == ATTENTION and "600m" in st.reason


def test_two_concerns_needs_attention_one_does_not():
    assert evaluate(healthy() + [note(DATES[1], "concern")], TH).state == ON_TRACK
    assert evaluate(healthy() + [note(DATES[1], "concern"), note(DATES[2], "injury", "whatsapp")],
                    TH).state == ATTENTION


def test_gap_from_few_sessions_or_no_midline():
    few = [att(d, "P") for d in DATES[:4]] + [assess("baseline"), assess("midline")]
    assert evaluate(few, TH).state == GAP
    no_mid = [att(d, "P") for d in DATES] + [assess("baseline")]
    assert "midline" in evaluate(no_mid, TH).reason


def test_conflict_wins_over_everything():
    facts = [att(d, "A") for d in DATES[:3]] + [note(DATES[0], "praise")]  # also a gap + low att
    st = evaluate(facts, TH)
    assert st.state == CONFLICT and len(st.evidence) == 2


def test_chat_praise_on_absent_day_is_not_a_conflict():
    facts = healthy(absent=[DATES[3]]) + [note(DATES[3], "praise", kind="whatsapp")]
    assert evaluate(facts, TH).state == ON_TRACK


def test_gap_beats_attention():
    facts = [att(d, "A") for d in DATES[:4]] + [assess("baseline"), assess("midline")]
    assert evaluate(facts, TH).state == GAP


def test_school_is_right_clears_conflict_and_keeps_absence():
    facts = healthy(absent=[DATES[3]]) + [note(DATES[3], "praise")]
    assert evaluate(facts, TH).state == CONFLICT
    st = evaluate(facts, TH, {DATES[3]: "school"})
    assert st.state == ON_TRACK and "11 of 12" in st.reason
    assert st.resolved == [{"date": DATES[3], "choice": "school"}]


def test_coach_is_right_counts_the_session():
    facts = healthy(absent=[DATES[3]]) + [note(DATES[3], "praise")]
    st = evaluate(facts, TH, {DATES[3]: "coach"})
    assert st.state == ON_TRACK and "12 of 12" in st.reason


def test_ask_coach_keeps_conflict_open():
    facts = healthy(absent=[DATES[3]]) + [note(DATES[3], "praise")]
    st = evaluate(facts, TH, {DATES[3]: "ask"})
    assert st.state == CONFLICT and "Waiting for the coach" in st.reason
