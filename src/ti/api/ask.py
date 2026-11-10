"""Ask: the browser model (or Ollama) sends a structured query; rules parse when no model."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select

from ti import ask
from ti.api.deps import current_user, get_db, scope
from ti.db import School

router = APIRouter(prefix="/api/ask")


class Question(BaseModel):
    question: str


@router.get("/prompt")
def prompt(allowed=Depends(scope), s=Depends(get_db)):
    q = select(School)
    if allowed is not None:
        q = q.where(School.id.in_(allowed))
    return ask.prompt([x.short for x in s.scalars(q)])


@router.post("/parse")
def parse(body: Question, user=Depends(current_user), s=Depends(get_db)):
    return ask.clean_spec(ask.parse(body.question, s.scalars(select(School)).all()))


class Run(BaseModel):
    spec: dict
    question: str = ""
    routed_by: str = "rules"


@router.post("/run")
def run(body: Run, allowed=Depends(scope), s=Depends(get_db)):
    spec = body.spec
    if body.question.strip():
        spec = ask.merge(spec, ask.parse(body.question, s.scalars(select(School)).all()))
    out = ask.run(s, spec, allowed)
    out["routed_by"] = body.routed_by
    out["question"] = body.question
    return out
