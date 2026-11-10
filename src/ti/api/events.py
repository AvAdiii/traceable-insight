"""Calendar, meets, meet items, AI shortlists, selections, results and to-dos."""

import csv
import datetime as dt
import io

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import delete, select

from ti import queries, shortlist
from ti.api.deps import current_user, get_db, planner, scope
from ti.db import Audit, Child, Event, EventItem, Result, School, Selection, Todo

router = APIRouter(prefix="/api")


class EventIn(BaseModel):
    title: str
    kind: str = "meet"
    level: str = "school"
    start_date: dt.date
    end_date: dt.date | None = None
    start_time: str = ""
    venue: str = ""
    notes: str = ""
    school_ids: list[str] = []


@router.get("/events")
def events(start: dt.date | None = None, end: dt.date | None = None, user=Depends(current_user),
           s=Depends(get_db)):
    q = select(Event).order_by(Event.start_date)
    if start:
        q = q.where(Event.start_date >= start)
    if end:
        q = q.where(Event.start_date <= end)
    return [queries.event_brief(s, e) for e in s.scalars(q)]


@router.post("/events")
def create_event(body: EventIn, user=Depends(planner), s=Depends(get_db)):
    e = Event(**body.model_dump(), created_by=user.id)
    s.add(e)
    s.commit()
    return queries.event_detail(s, e.id)


@router.get("/events/{eid}")
def event(eid: int, user=Depends(current_user), s=Depends(get_db)):
    d = queries.event_detail(s, eid)
    if d is None:
        raise HTTPException(404, "Event not found")
    return d


@router.patch("/events/{eid}")
def patch_event(eid: int, body: dict, user=Depends(planner), s=Depends(get_db)):
    e = s.get(Event, eid)
    if e is None:
        raise HTTPException(404, "Event not found")
    data = EventIn(**{**queries.event_brief(s, e), **body}).model_dump()
    for k, v in data.items():
        setattr(e, k, v)
    s.commit()
    return queries.event_detail(s, eid)


@router.delete("/events/{eid}")
def delete_event(eid: int, user=Depends(planner), s=Depends(get_db)):
    e = s.get(Event, eid)
    if e:
        ids = [i.id for i in s.scalars(select(EventItem).where(EventItem.event_id == eid))]
        if ids:
            s.execute(delete(Selection).where(Selection.item_id.in_(ids)))
            s.execute(delete(Result).where(Result.item_id.in_(ids)))
        s.execute(delete(EventItem).where(EventItem.event_id == eid))
        s.execute(delete(Todo).where(Todo.event_id == eid))
        s.delete(e)
        s.commit()
    return {"ok": True}


class ItemIn(BaseModel):
    name: str
    discipline: str
    gender: str = "Any"
    age_min: int | None = None
    age_max: int | None = None
    slots: int = 3
    reserves: int = 2


@router.post("/events/{eid}/items")
def add_item(eid: int, body: ItemIn, user=Depends(planner), s=Depends(get_db)):
    if body.discipline not in shortlist.DISCIPLINES:
        raise HTTPException(422, "Unknown discipline")
    it = EventItem(event_id=eid, **body.model_dump())
    s.add(it)
    s.commit()
    return queries.event_detail(s, eid)


@router.patch("/items/{iid}")
def patch_item(iid: int, body: ItemIn, user=Depends(planner), s=Depends(get_db)):
    it = s.get(EventItem, iid)
    if it is None:
        raise HTTPException(404, "Item not found")
    for k, v in body.model_dump().items():
        setattr(it, k, v)
    s.commit()
    return queries.event_detail(s, it.event_id)


@router.delete("/items/{iid}")
def delete_item(iid: int, user=Depends(planner), s=Depends(get_db)):
    it = s.get(EventItem, iid)
    if it is None:
        return {"ok": True}
    eid = it.event_id
    s.execute(delete(Selection).where(Selection.item_id == iid))
    s.execute(delete(Result).where(Result.item_id == iid))
    s.delete(it)
    s.commit()
    return queries.event_detail(s, eid)


@router.get("/items/{iid}/suggest")
def suggest(iid: int, allowed=Depends(scope), s=Depends(get_db)):
    it = s.get(EventItem, iid)
    if it is None:
        raise HTTPException(404, "Item not found")
    out = shortlist.suggest(s, it, allowed)
    chosen = {sel.child_id: sel.status for sel in s.scalars(select(Selection).where(Selection.item_id == iid))}
    for group in ("selected", "reserves", "more"):
        for c in out[group]:
            c["chosen"] = chosen.get(c["child_id"])
    out["item"] = {"id": it.id, "name": it.name, "gender": it.gender, "age_min": it.age_min,
                   "age_max": it.age_max, "slots": it.slots, "reserves": it.reserves,
                   "discipline": it.discipline}
    return out


class Pick(BaseModel):
    child_id: str
    status: str = "selected"   # selected | reserve | none
    summary: str = ""


@router.post("/items/{iid}/selections")
def pick(iid: int, body: Pick, user=Depends(planner), s=Depends(get_db)):
    it = s.get(EventItem, iid)
    if it is None or s.get(Child, body.child_id) is None:
        raise HTTPException(404, "Not found")
    sel = s.scalar(select(Selection).where(Selection.item_id == iid, Selection.child_id == body.child_id))
    if body.status == "none":
        if sel:
            s.delete(sel)
    else:
        n = len(s.scalars(select(Selection).where(Selection.item_id == iid, Selection.status == body.status)).all())
        if sel:
            sel.status = body.status
        else:
            s.add(Selection(item_id=iid, child_id=body.child_id, status=body.status, rank=n + 1,
                            reason={"summary": body.summary}))
    s.add(Audit(user_id=user.id, action="select", detail={"item": iid, **body.model_dump()}))
    s.commit()
    return queries.event_detail(s, it.event_id)


@router.post("/items/{iid}/accept")
def accept(iid: int, allowed=Depends(scope), user=Depends(planner), s=Depends(get_db)):
    """Take the suggestion as it stands: top slots selected, next ones as reserves."""
    it = s.get(EventItem, iid)
    if it is None:
        raise HTTPException(404, "Item not found")
    sug = shortlist.suggest(s, it, allowed)
    s.execute(delete(Selection).where(Selection.item_id == iid))
    for status, group in (("selected", sug["selected"]), ("reserve", sug["reserves"])):
        for rank, c in enumerate(group, start=1):
            s.add(Selection(item_id=iid, child_id=c["child_id"], status=status, rank=rank,
                            reason={"summary": c["summary"], "score": c["score"]}))
    s.add(Audit(user_id=user.id, action="accept_shortlist", detail={"item": iid}))
    s.commit()
    return queries.event_detail(s, it.event_id)


class ResultIn(BaseModel):
    child_id: str
    position: int | None = None
    mark: str = ""
    note: str = ""


@router.post("/items/{iid}/results")
def result(iid: int, body: ResultIn, user=Depends(planner), s=Depends(get_db)):
    it = s.get(EventItem, iid)
    if it is None:
        raise HTTPException(404, "Item not found")
    r = s.scalar(select(Result).where(Result.item_id == iid, Result.child_id == body.child_id))
    if r is None:
        r = Result(item_id=iid, child_id=body.child_id)
        s.add(r)
    r.position, r.mark, r.note = body.position, body.mark, body.note
    s.commit()
    return queries.event_detail(s, it.event_id)


@router.get("/events/{eid}/export.csv")
def export(eid: int, user=Depends(current_user), s=Depends(get_db)):
    d = queries.event_detail(s, eid)
    if d is None:
        raise HTTPException(404, "Event not found")
    schools = {x.id: x.name for x in s.scalars(select(School))}
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["Event", "Item", "Status", "Rank", "Student Name", "Class", "Gender", "School", "Why"])
    for it in d["items_detail"]:
        for sel in it["selections"]:
            w.writerow([d["title"], f"{it['name']} ({it['gender']})", sel["status"], sel["rank"],
                        sel["name"], sel["klass"], sel["gender"], schools.get(sel["school_id"], ""),
                        sel["summary"]])
    name = d["title"].replace(" ", "_") + ".csv"
    return StreamingResponse(iter([buf.getvalue()]), media_type="text/csv",
                             headers={"Content-Disposition": f'attachment; filename="{name}"'})


class TodoIn(BaseModel):
    text: str
    event_id: int | None = None
    due_date: dt.date | None = None
    done: bool = False


@router.get("/todos")
def todos(user=Depends(current_user), s=Depends(get_db)):
    return [queries.todo_dict(t) for t in s.scalars(select(Todo).order_by(Todo.done, Todo.due_date))]


@router.post("/todos")
def add_todo(body: TodoIn, user=Depends(current_user), s=Depends(get_db)):
    t = Todo(**body.model_dump())
    s.add(t)
    s.commit()
    return queries.todo_dict(t)


@router.patch("/todos/{tid}")
def patch_todo(tid: int, body: dict, user=Depends(current_user), s=Depends(get_db)):
    t = s.get(Todo, tid)
    if t is None:
        raise HTTPException(404, "To-do not found")
    if "done" in body:
        t.done = bool(body["done"])
    if "text" in body:
        t.text = str(body["text"])[:300]
    if "due_date" in body:
        t.due_date = dt.date.fromisoformat(body["due_date"]) if body["due_date"] else None
    s.commit()
    return queries.todo_dict(t)


@router.delete("/todos/{tid}")
def delete_todo(tid: int, user=Depends(current_user), s=Depends(get_db)):
    t = s.get(Todo, tid)
    if t:
        s.delete(t)
        s.commit()
    return {"ok": True}
