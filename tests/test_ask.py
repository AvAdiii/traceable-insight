from ti import ask, pipeline
from ti.llm import FakeClient
from ti.store import db
from tests.test_pipeline import names_in


def _conn(school_dir, tmp_path):
    pipeline.run("school_t", FakeClient(fn=names_in), db_path=tmp_path / "a.db",
                 data_dir=school_dir.parent, log=lambda *_: None)
    return db.connect(tmp_path / "a.db")


def test_model_route_used_and_answer_comes_from_store(school_dir, tmp_path):
    c = _conn(school_dir, tmp_path)
    client = FakeClient(responses=[{"intent": "conflicts", "n": None, "name": None}])
    a = ask.answer(c, "who has clashing records?", client)
    states = dict(c.execute("SELECT child_id, state FROM child_states"))
    assert a.routed_by == "model" and a.child_ids
    assert all(states[x] == "Conflict to review" for x in a.child_ids)


def test_missed_sessions_uses_sheet_counts(school_dir, tmp_path):
    c = _conn(school_dir, tmp_path)
    a = ask.answer(c, "missed more than 5", FakeClient(
        responses=[{"intent": "missed_sessions", "n": 5, "name": None}]))
    for cid in a.child_ids:
        n = c.execute("SELECT COUNT(*) FROM facts WHERE child_id=? AND type='attendance' AND "
                      "json_extract(value,'$.mark')='A'", (cid,)).fetchone()[0]
        assert n > 5


def test_bad_model_output_falls_back_to_keywords(school_dir, tmp_path):
    c = _conn(school_dir, tmp_path)
    a = ask.answer(c, "show conflicts please", FakeClient(responses=[{"intent": "dance"}]))
    assert a.routed_by == "keywords" and a.intent == "conflicts"
