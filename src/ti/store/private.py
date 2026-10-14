"""Local, git-ignored copy of the original source lines and quotes.

The SQLite store holds pseudonymised text: once a name is linked it is replaced by the
child's roster id, e.g. "[A03] ran well". The original wording stays here, on this machine
only, so every citation can still open the exact line it came from.
"""

import json
import re
from functools import lru_cache
from pathlib import Path

from ti import config


def path(school: str, base: Path | None = None) -> Path:
    return (base or config.PRIVATE_DIR) / school / "originals.json"


def token(child_id: str) -> str:
    return f"[{child_id}]"


def pseudonymise(text: str, pairs: list[tuple[str, str]]) -> str:
    """Replace each linked surface (longest first, whole words) with its roster id."""
    for surface, cid in sorted(set(pairs), key=lambda p: -len(p[0])):
        text = re.sub(rf"(?<![\w]){re.escape(surface)}(?![\w])", token(cid), text)
    return text


def write(p: Path, lines: dict[int, str], facts: dict[int, dict]) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"lines": lines, "facts": facts}, ensure_ascii=False))
    load.cache_clear()


@lru_cache(maxsize=4)
def _load(p: str, mtime: float) -> dict:
    raw = json.loads(Path(p).read_text())
    return {"lines": {int(k): v for k, v in raw["lines"].items()},
            "facts": {int(k): v for k, v in raw["facts"].items()}}


def load(p: Path | str | None) -> dict:
    """Originals for a run, or empty maps when the private copy is not on this machine."""
    if not p or not Path(p).exists():
        return {"lines": {}, "facts": {}}
    return _load(str(p), Path(p).stat().st_mtime)


load.cache_clear = _load.cache_clear
