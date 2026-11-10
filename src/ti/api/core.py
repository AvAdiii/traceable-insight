"""Sign-in, workspace meta, overview, children, schools and the cell receipt."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from ti import auth, queries
from ti.api.deps import current_user, get_db, scope
from ti.db import User

router = APIRouter(prefix="/api")


class Login(BaseModel):
    email: str
    password: str


@router.post("/auth/login")
def login(body: Login, s=Depends(get_db)):
    u = s.scalar(select(User).where(User.email == body.email.strip().lower()))
    if u is None or not auth.check_password(body.password, u.password_hash):
        raise HTTPException(401, "Email or password is not right")
    return {"token": auth.token(u), "user": queries.user_dict(u)}


@router.get("/meta")
def meta(user=Depends(current_user), allowed=Depends(scope), s=Depends(get_db)):
    return queries.meta(s, user, allowed)


@router.get("/overview")
def overview(allowed=Depends(scope), s=Depends(get_db)):
    return queries.overview(s, allowed)


@router.get("/children")
def children(q: str | None = None, school: str | None = None, klass: str | None = None,
             gender: str | None = None, age_min: float | None = None, age_max: int | None = None,
             flag: str | None = None, test: str | None = None, sort: str = "best",
             round_id: int | None = None, coach: str | None = None, limit: int = 60, offset: int = 0,
             allowed=Depends(scope), s=Depends(get_db)):
    return queries.children(s, allowed, q=q, school=school, klass=klass, gender=gender,
                            age_min=age_min, age_max=age_max, flag=flag, test=test, sort=sort,
                            round_id=round_id, coach=coach, limit=min(limit, 500), offset=offset)


@router.get("/children/{cid}")
def child(cid: str, allowed=Depends(scope), s=Depends(get_db)):
    d = queries.child_detail(s, cid, allowed)
    if d is None:
        raise HTTPException(404, "Child not found")
    return d


@router.get("/receipt/{record_id}")
def receipt(record_id: int, field: str | None = None, col: str | None = None, allowed=Depends(scope), s=Depends(get_db)):
    d = queries.receipt(s, record_id, field, allowed, col=col)
    if d is None:
        raise HTTPException(404, "Row not found")
    return d


@router.get("/schools")
def schools(allowed=Depends(scope), s=Depends(get_db)):
    return queries.schools_summary(s, allowed)


@router.get("/schools/{sid}")
def school(sid: str, allowed=Depends(scope), s=Depends(get_db)):
    d = queries.school_detail(s, sid, allowed)
    if d is None:
        raise HTTPException(404, "School not found")
    return d
