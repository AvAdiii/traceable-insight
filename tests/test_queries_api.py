import pytest
from fastapi.testclient import TestClient

from ti import config, pipeline, queries
from ti.llm import FakeClient
from ti.store import db
from tests.test_pipeline import names_in


@pytest.fixture(scope="module")
def run_db(school_dir, tmp_path_factory, request):
    path = tmp_path_factory.mktemp("run") / "school_t.db"
    pipeline.run("school_t", FakeClient(fn=names_in), db_path=path,
                 data_dir=school_dir.parent, log=lambda *_: None)
    return path


def test_overview_has_every_child_once(run_db):
    ov = queries.school_overview(db.connect(run_db))
    ids = [c["child_id"] for g in ov["groups"].values() for c in g]
    assert len(ids) == len(set(ids)) == 25
    assert "score" not in str(ov["groups"]).lower()


def test_child_detail_evidence_cites_real_lines(run_db):
    conn = db.connect(run_db)
    ov = queries.school_overview(conn)
    gap = ov["groups"]["Not enough information"][0]
    d = queries.child_detail(conn, gap["child_id"])
    assert d["rules"] and d["rules"][0]["source_file"] == "guideline.md"
    for f in d["facts"]:
        ctx = queries.source_context(conn, f["line_id"])
        cited = next(l for l in ctx["lines"] if l["cited"])
        assert f["quote"] in cited["text"]


def test_resolve_review_item(run_db):
    conn = db.connect(run_db)
    q = queries.review_queue(conn)
    assert q, "fake run should leave at least one ambiguous mention"
    item = q[0]
    queries.resolve_mention(conn, item["mention_id"], item["candidates"][0]["child_id"])
    assert all(i["mention_id"] != item["mention_id"] for i in queries.review_queue(conn))
    assert len(db.overrides(conn)) == 1


def test_api_endpoints(run_db, monkeypatch):
    from ti.api import app
    monkeypatch.setattr(config, "db_path", lambda school: run_db)
    c = TestClient(app)
    ov = c.get("/schools/school_t").json()
    cid = ov["groups"]["On track"][0]["child_id"]
    d = c.get(f"/schools/school_t/children/{cid}").json()
    assert d["state"] == "On track"
    line = d["facts"][0]["line_id"]
    assert c.get(f"/schools/school_t/sources/{line}").json()["line_id"] == line
    assert c.get("/schools/school_t/children/ZZZ").status_code == 404
    assert isinstance(c.get("/schools/school_t/review").json(), list)


def test_review_candidates_are_plausible_only():
    from ti.store import db as dbm
    conn = dbm.connect(":memory:")
    dbm.init(conn)
    dbm.insert_children(conn, [
        {"child_id": "A1", "first": "Ravi", "surname": "Kumar", "class": "6", "age": 11, "gender": "M"},
        {"child_id": "A2", "first": "Ravi", "surname": "Shankar", "class": "6", "age": 11, "gender": "M"},
        {"child_id": "A3", "first": "Tanvi", "surname": "Verma", "class": "6", "age": 11, "gender": "F"}])
    from ti.ingest.parsers import SourceLine
    ids = dbm.insert_lines(conn, [SourceLine("w.txt", "msg:1", "ravi aaya", "whatsapp", {})])
    dbm.insert_mention(conn, ids[("w.txt", "msg:1")], "ravi", "review", None, 100,
                       [("A1", 100), ("A2", 100), ("A3", 78)])
    q = queries.review_queue(conn)
    assert [c["child_id"] for c in q[0]["candidates"]] == ["A1", "A2"]
