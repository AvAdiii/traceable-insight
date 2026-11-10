"""Uploads, rounds, the Inbox and programme settings."""

import datetime as dt

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy import select

from ti import pipeline, queries
from ti.api.deps import current_user, get_db, manager, scope
from ti.db import Audit, Issue, Round, School, Setting, Upload, User

router = APIRouter(prefix="/api")


@router.get("/uploads")
def uploads(allowed=Depends(scope), s=Depends(get_db)):
    users = {u.id: u.name for u in s.scalars(select(User))}
    rounds = {r.id: r.label for r in s.scalars(select(Round))}
    out = []
    for u in s.scalars(select(Upload).order_by(Upload.uploaded_at.desc())):
        out.append({"id": u.id, "filename": u.filename, "sha256": u.sha256, "size": u.size,
                    "round": rounds.get(u.round_id), "uploaded_by": users.get(u.uploaded_by),
                    "uploaded_at": u.uploaded_at.isoformat(), "status": u.status,
                    "summary": u.summary, "sheets": list(u.sheets)})
    return out


@router.post("/uploads")
async def upload(file: UploadFile = File(...), round_id: int | None = Form(None),
                 round_label: str | None = Form(None), round_kind: str = Form("custom"),
                 test_date: str | None = Form(None), user=Depends(current_user), s=Depends(get_db)):
    data = await file.read()
    if len(data) > 25 * 1024 * 1024:
        raise HTTPException(413, "File is larger than 25 MB")
    if round_id is None:
        if not round_label or not test_date:
            raise HTTPException(422, "Choose a round, or give the new round a name and test date")
        r = s.scalar(select(Round).where(Round.label == round_label))
        if r is None:
            r = Round(label=round_label, kind=round_kind, test_date=dt.date.fromisoformat(test_date))
            s.add(r)
            s.flush()
        round_id = r.id
    try:
        up = pipeline.ingest_upload(s, data, file.filename or "upload.xlsx", round_id, user.id)
    except pipeline.Refused as e:
        s.rollback()
        raise HTTPException(422, str(e)) from e
    s.add(Audit(user_id=user.id, action="upload", detail={"upload": up.id, "file": up.filename}))
    s.commit()
    return {"id": up.id, "filename": up.filename, "summary": up.summary}


@router.get("/rounds")
def rounds(user=Depends(current_user), s=Depends(get_db)):
    return [queries.round_dict(r) for r in queries.rounds(s)]


@router.get("/inbox")
def inbox(status: str = "open", kind: str | None = None, school: str | None = None,
          allowed=Depends(scope), s=Depends(get_db)):
    return queries.inbox(s, allowed, status, kind, school)


class Resolve(BaseModel):
    key: str
    option_id: str
    value: float | None = None


@router.post("/inbox/resolve")
def resolve(body: Resolve, user=Depends(current_user), allowed=Depends(scope), s=Depends(get_db)):
    issue = s.scalar(select(Issue).where(Issue.key == body.key))
    if issue is None or (allowed is not None and issue.school_id not in allowed):
        raise HTTPException(404, "Item not found")
    opt = next((o for o in issue.options if o["id"] == body.option_id), None)
    if opt is None:
        raise HTTPException(422, "Unknown choice")
    payload = dict(opt["payload"])
    if opt.get("input"):
        if body.value is None:
            raise HTTPException(422, "Enter a value")
        payload["value"] = body.value
    pipeline.resolve(s, body.key, payload, user.id)
    s.add(Audit(user_id=user.id, action="resolve", detail={"key": body.key, "payload": payload}))
    s.commit()
    return {"ok": True, "open": queries.inbox(s, allowed)["open"]}


class Key(BaseModel):
    key: str


@router.post("/inbox/undo")
def undo(body: Key, user=Depends(current_user), s=Depends(get_db)):
    pipeline.undo(s, body.key)
    s.add(Audit(user_id=user.id, action="undo", detail={"key": body.key}))
    s.commit()
    return {"ok": True}


@router.get("/settings")
def get_settings(user=Depends(current_user), s=Depends(get_db)):
    return pipeline.settings(s)


@router.put("/settings")
def put_settings(body: dict, user=Depends(manager), s=Depends(get_db)):
    row = s.get(Setting, "programme") or Setting(key="programme", value={})
    allowed_keys = {"weights", "flags", "placeholder_share"}
    row.value = {**row.value, **{k: v for k, v in body.items() if k in allowed_keys}}
    s.merge(row)
    s.flush()
    pipeline.rebuild(s)
    s.commit()
    return pipeline.settings(s)


class SchoolPatch(BaseModel):
    short: str | None = None
    area: str | None = None
    trainer_id: int | None = None
    supervisor_id: int | None = None


@router.patch("/schools/{sid}")
def patch_school(sid: str, body: SchoolPatch, user=Depends(manager), s=Depends(get_db)):
    x = s.get(School, sid)
    if x is None:
        raise HTTPException(404, "School not found")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(x, k, v)
    s.commit()
    return {"ok": True}
