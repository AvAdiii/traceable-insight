from ti.ingest.parsers import SourceLine
from ti.store import db, thresholds


def test_schema_and_overrides_survive_reinit(tmp_path):
    conn = db.connect(tmp_path / "t.db")
    db.init(conn)
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"children", "source_lines", "mentions", "facts", "child_states",
            "link_overrides", "run_meta"} <= tables
    conn.execute("INSERT INTO link_overrides (source_file, ref, surface, child_id) "
                 "VALUES ('w.txt', 'msg:1', 'ravi', 'A03')")
    db.init(conn)
    assert db.overrides(conn) == {("w.txt", "msg:1", "ravi"): "A03"}


def test_insert_lines_returns_ids(tmp_path):
    conn = db.connect(":memory:")
    db.init(conn)
    ids = db.insert_lines(conn, [SourceLine("a.csv", "row:1", "x", "attendance", {"k": 1})])
    assert conn.execute("SELECT text FROM source_lines WHERE line_id=?",
                        (ids[("a.csv", "row:1")],)).fetchone()[0] == "x"


def test_thresholds_load(school_dir):
    t = thresholds.load(school_dir.parent / "programme" / "thresholds.yaml")
    assert t["synthetic"] is True and t["attendance_rate_min"] == 0.6


def test_reinit_on_populated_store(tmp_path):
    conn = db.connect(tmp_path / "t.db")
    db.init(conn)
    db.insert_children(conn, [{"child_id": "A01", "first": "X", "surname": "Y", "class": "6",
                               "age": 11, "gender": "F"}])
    ids = db.insert_lines(conn, [SourceLine("a.csv", "row:1", "X Y,P", "attendance", {})])
    mid = db.insert_mention(conn, ids[("a.csv", "row:1")], "X Y", "linked", "A01", 100, [])
    db.insert_fact(conn, {"line_id": ids[("a.csv", "row:1")], "mention_id": mid,
                          "child_id": "A01", "type": "attendance", "date": "2026-07-07",
                          "quote": "X Y,P", "summary": "Present", "extractor": "rule"})
    conn.commit()
    db.init(conn)
    assert conn.execute("SELECT COUNT(*) FROM facts").fetchone()[0] == 0


def test_pseudonymise_whole_words_longest_first():
    from ti.store.private import pseudonymise
    text = "Ravi Kumar ran; Ravi K came late; Ravindra stayed"
    out = pseudonymise(text, [("Ravi Kumar", "A03"), ("Ravi K", "A03")])
    assert out == "[A03] ran; [A03] came late; Ravindra stayed"
