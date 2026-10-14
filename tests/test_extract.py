from ti.extract import extract_line, find_span, verify
from ti.ingest.parsers import SourceLine
from ti.llm import FakeClient

NOTE = "Hot day. Suresh kept good form till the last lap. Priya seemed very tired."


def test_fabricated_quote_and_name_rejected():
    assert verify({"name": "Kiran", "type": "praise", "quote": "Kiran ran"}, NOTE) is None


def test_garbled_quote_repaired_to_exact_span():
    v = verify({"name": "Suresh", "type": "praise",
                "quote": "Sures: kept good form till the last lap"}, NOTE)
    assert v["quote"] in NOTE and "Suresh" in v["quote"]


def test_name_case_pinned_to_source():
    v = verify({"name": "PRIYA", "type": "concern", "quote": "priya seemed very tired"}, NOTE)
    assert v["name"] == "Priya" and v["quote"] == "Priya seemed very tired"


def test_find_span_never_invents_text():
    assert find_span("completely different words", NOTE) is None


def test_attendance_row_gives_a_fact_only_when_recorded():
    line = SourceLine("attendance_wk1.csv", "row:1", "07-07-2026,Tue,Ravi K.,P", "attendance",
                      {"name": "Ravi K.", "marks": {"2026-07-07": "P"}})
    facts, rej = extract_line(line, FakeClient())
    assert len(facts) == 1 and facts[0]["value"] == {"mark": "P"} and rej == 0
    assert facts[0]["quote"] == line.text
    blank = SourceLine("attendance_wk1.csv", "row:2", "07-07-2026,Tue,Gopal Patel,",
                       "attendance", {"name": "Gopal Patel", "marks": {"2026-07-07": None}})
    assert extract_line(blank, FakeClient()) == ([], 0)


def test_blank_assessment_row_is_a_cited_missing_result():
    line = SourceLine("assessments.csv", "row:30", "midline,14-08-2026,Gopal Patel,,,",
                      "assessment", {"round": "midline", "date": "2026-08-14",
                                     "name": "Gopal Patel", "sprint_50m_s": None,
                                     "broad_jump_cm": None, "run_600m_s": None})
    facts, _ = extract_line(line, FakeClient())
    assert facts[0]["value"] == {"round": "midline", "missing": True}


def test_llm_path_drops_bad_items():
    line = SourceLine("whatsapp.txt", "msg:4", "aaj Bharat nahi aaya", "whatsapp",
                      {"date": "2026-07-07"})
    client = FakeClient(responses=[{"facts": [
        {"name": "Bharat", "type": "absence", "quote": "Bharat nahi aaya"},
        {"name": "Ghost", "type": "praise", "quote": "Ghost ran"},
        "junk"]}])
    facts, rej = extract_line(line, client)
    assert [f["name"] for f in facts] == ["Bharat"] and rej == 2
    assert facts[0]["date"] == "2026-07-07"


def test_truncated_name_grows_to_whole_word():
    text = "aaj 50m sprint mein Siddharth ne first ho gaya"
    v = verify({"name": "Siddhart", "type": "praise", "quote": "Siddharth ne first"}, text)
    assert v["name"] == "Siddharth"
