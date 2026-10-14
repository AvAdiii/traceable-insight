"""Minimal Ollama client: JSON generation with a content-addressed disk cache.

Every call is deterministic (temperature 0, fixed seed) and cached by a hash of
model + system + prompt, so repeat runs never hit the model.
"""

import hashlib
import json
from pathlib import Path

import httpx

from ti import config


class OllamaUnavailable(RuntimeError):
    pass


class OllamaClient:
    def __init__(self, model: str = config.MODEL, url: str = config.OLLAMA_URL,
                 cache_dir: Path | None = None, timeout: float = 180.0):
        self.model = model
        self.url = url.rstrip("/")
        self.cache_dir = cache_dir or config.VAR_DIR / "llm_cache"
        self.timeout = timeout
        self.calls = 0

    def _key(self, prompt: str, system: str) -> str:
        blob = json.dumps([self.model, system, prompt], ensure_ascii=False)
        return hashlib.sha256(blob.encode()).hexdigest()

    def check(self) -> None:
        """Raise OllamaUnavailable unless the server is up and the model is pulled."""
        try:
            tags = httpx.get(f"{self.url}/api/tags", timeout=5).json()
        except httpx.HTTPError as e:
            raise OllamaUnavailable(
                f"Ollama not reachable at {self.url}. Start it with `ollama serve`.") from e
        names = {m["name"] for m in tags.get("models", [])}
        if self.model not in names:
            raise OllamaUnavailable(
                f"Model {self.model!r} not pulled. Run `ollama pull {self.model}`.")

    def generate_json(self, prompt: str, system: str = "") -> dict:
        path = self.cache_dir / f"{self._key(prompt, system)}.json"
        if path.exists():
            return json.loads(path.read_text())
        body = {
            "model": self.model, "prompt": prompt, "system": system,
            "format": "json", "stream": False, "think": False,
            "options": {"temperature": 0, "seed": config.SEED},
        }
        try:
            r = httpx.post(f"{self.url}/api/generate", json=body, timeout=self.timeout)
            r.raise_for_status()
        except httpx.HTTPError as e:
            raise OllamaUnavailable(f"Ollama request failed: {e}") from e
        self.calls += 1
        try:
            out = json.loads(r.json()["response"])
        except json.JSONDecodeError:
            out = {}
        if not isinstance(out, dict):
            out = {"value": out}
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(out, ensure_ascii=False))
        return out


class FakeClient:
    """Test double: returns queued responses, or calls a function of the prompt."""

    def __init__(self, responses=None, fn=None):
        self.responses = list(responses or [])
        self.fn = fn
        self.prompts: list[str] = []

    def check(self) -> None:
        pass

    def generate_json(self, prompt: str, system: str = "") -> dict:
        self.prompts.append(prompt)
        if self.fn:
            return self.fn(prompt)
        return self.responses.pop(0)
