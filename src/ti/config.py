"""Paths and runtime settings. Override with TI_* environment variables.

TI_DATABASE_URL picks the store: SQLite file locally (default), Postgres (Supabase) when hosted.
"""

import os
from pathlib import Path

ROOT = Path(os.environ.get("TI_ROOT", Path(__file__).resolve().parents[2]))
VAR_DIR = Path(os.environ.get("TI_VAR", ROOT / "var"))
DEMO_DIR = ROOT / "data" / "demo"
UPLOAD_DIR = Path(os.environ.get("TI_UPLOADS", VAR_DIR / "uploads"))
WEB_DIST = ROOT / "web" / "dist"

DATABASE_URL = os.environ.get("TI_DATABASE_URL", f"sqlite:///{VAR_DIR / 'ti.db'}")
SECRET = os.environ.get("TI_SECRET", "dev-only-secret-change-me-before-hosting-0000")
TOKEN_HOURS = int(os.environ.get("TI_TOKEN_HOURS", "72"))
CORS_ORIGINS = [o for o in os.environ.get("TI_CORS", "http://localhost:5173").split(",") if o]
SEED = 42
