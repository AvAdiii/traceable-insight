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
