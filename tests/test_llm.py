import json

import httpx
import pytest

from ti.llm import OllamaClient, OllamaUnavailable


def test_cache_hit_skips_http(tmp_path, monkeypatch):
    client = OllamaClient(cache_dir=tmp_path)
    sent = []

    def fake_post(url, json=None, timeout=None):
        sent.append(json)
        return httpx.Response(200, json={"response": '{"ok": 1}'},
                              request=httpx.Request("POST", url))

    monkeypatch.setattr(httpx, "post", fake_post)
    assert client.generate_json("hi") == {"ok": 1}
    assert client.generate_json("hi") == {"ok": 1}
    assert len(sent) == 1
    assert sent[0]["format"] == "json" and sent[0]["model"] == "qwen2.5:7b"
    assert "think" not in sent[0]  # qwen2.5 is not a thinking model


def test_unreachable_server_raises(tmp_path):
    client = OllamaClient(url="http://127.0.0.1:9", cache_dir=tmp_path)
    with pytest.raises(OllamaUnavailable):
        client.check()
    with pytest.raises(OllamaUnavailable):
        client.generate_json("hi")


def test_bad_json_becomes_empty_dict(tmp_path, monkeypatch):
    client = OllamaClient(cache_dir=tmp_path)
    monkeypatch.setattr(httpx, "post", lambda url, json=None, timeout=None: httpx.Response(
        200, json={"response": "not json"}, request=httpx.Request("POST", url)))
    assert client.generate_json("x") == {}
