"""FastAPI app: `uv run uvicorn ti.api:app --reload`. Serves the built web app at / when present."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from ti import config, db
from ti.api import ask, core, data, events

app = FastAPI(title="Stride", version="2.0.0")
app.add_middleware(CORSMiddleware, allow_origins=config.CORS_ORIGINS, allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])
for r in (core.router, data.router, events.router, ask.router):
    app.include_router(r)


@app.on_event("startup")
def _startup():
    db.create_all()


@app.get("/api/health")
def health():
    return {"ok": True}


dist = Path(config.WEB_DIST)
if dist.exists():
    app.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str):
        f = dist / path
        if path and f.is_file():
            return FileResponse(f)
        return FileResponse(dist / "index.html")
