import re

import pytest

from ti import pipeline, score
from ti.llm import FakeClient, OllamaClient, OllamaUnavailable


def names_in(prompt: str) -> dict:
    """Fake extractor: capitalised words of the final text become 'participation' facts."""
    text = prompt.rsplit("Text: ", 1)[1].strip()
    skip = {"Good", "Hot", "Mixed", "Relay", "Speed", "Ground", "Class", "aaj"}
    words = [w for w in re.findall(r"\b[A-Z][a-z]{2,}\b", text) if w not in skip]
    return {"facts": [{"name": w, "type": "participation", "quote": w} for w in words]}


def test_pipeline_end_to_end_with_fake_model(school_dir, tmp_path):
    summary = pipeline.run("school_t", FakeClient(fn=names_in), db_path=tmp_path / "t.db",
                           data_dir=school_dir.parent, log=lambda *_: None)
    assert sum(summary["states"].values()) == 25
    res = score.compute("school_t", db_path=tmp_path / "t.db", data_dir=school_dir.parent)
    assert res["citations_resolve"] == 1.0
    assert res["gaps_recovered"] == 4


@pytest.mark.ollama
def test_real_model_meets_targets(tmp_path):
    client = OllamaClient()
    try:
        client.check()
    except OllamaUnavailable as e:
        pytest.skip(str(e))
    pipeline.run("school_a", client, db_path=tmp_path / "a.db", log=lambda *_: None)
    res = score.compute("school_a", db_path=tmp_path / "a.db")
    assert res["all_targets_met"], res["targets"]


def test_store_is_pseudonymised_and_originals_are_private(school_dir, tmp_path):
    import json
    from ti.store import db, private
    pipeline.run("school_t", FakeClient(fn=names_in), db_path=tmp_path / "p.db",
                 data_dir=school_dir.parent, log=lambda *_: None, private_dir=tmp_path / "priv")
    conn = db.connect(tmp_path / "p.db")
    roster = {r["child_id"]: r for r in conn.execute("SELECT * FROM children")}
    att = conn.execute("SELECT line_id, text FROM source_lines WHERE kind='attendance'").fetchall()
    linked = [t for _, t in att if "[A" in t]
    assert len(linked) > 250  # nearly every sheet row names a linked child
    full_names = [f"{c['first']} {c['surname']}" for c in roster.values()]
    assert not any(n in t for _, t in att for n in full_names if "[A" in t)
    orig = private.load(private.path("school_t", tmp_path / "priv"))
    assert all("[A" not in orig["lines"][lid] for lid, _ in att)
    meta = {k: json.loads(v) for k, v in conn.execute("SELECT key, value FROM run_meta")}
    assert meta["private_copy"].startswith(str(tmp_path / "priv"))
