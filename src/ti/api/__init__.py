"""A7 thin API over ti.queries: `uv run uvicorn ti.api:app`."""

from fastapi import FastAPI, HTTPException

from ti import config, queries
from ti.store import db

app = FastAPI(title="Traceable Insight", version="0.1.0")


def _conn(school: str):
    path = config.db_path(school)
    if not path.exists():
        raise HTTPException(404, f"No run for {school}. Run run_pipeline.py first.")
    return db.connect(path)


@app.get("/schools/{school}")
def school(school: str):
    return queries.school_overview(_conn(school))


@app.get("/schools/{school}/children/{child_id}")
def child(school: str, child_id: str):
    out = queries.child_detail(_conn(school), child_id)
    if out is None:
        raise HTTPException(404, "child not found")
    return out


@app.get("/schools/{school}/sources/{line_id}")
def source(school: str, line_id: int, radius: int = 2):
    out = queries.source_context(_conn(school), line_id, radius)
    if out is None:
        raise HTTPException(404, "source line not found")
    return out


@app.get("/schools/{school}/review")
def review(school: str):
    return queries.review_queue(_conn(school))
