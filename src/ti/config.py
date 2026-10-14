"""Project paths and runtime settings. Override with TI_* environment variables."""

import os
from pathlib import Path

ROOT = Path(os.environ.get("TI_ROOT", Path(__file__).resolve().parents[2]))
DATA_DIR = ROOT / "data" / "synthetic"
VAR_DIR = Path(os.environ.get("TI_VAR", ROOT / "var"))
CONFIG_DIR = ROOT / "config"
# Original (un-pseudonymised) source lines live here, outside git, so citations can open them.
PRIVATE_DIR = Path(os.environ.get("TI_PRIVATE", ROOT / "data" / "private"))

OLLAMA_URL = os.environ.get("TI_OLLAMA_URL", "http://localhost:11434")
MODEL = os.environ.get("TI_OLLAMA_MODEL", "qwen2.5:7b")
SEED = 7


def db_path(school: str) -> Path:
    return VAR_DIR / f"{school}.db"
