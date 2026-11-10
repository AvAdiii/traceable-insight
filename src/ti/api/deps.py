"""Shared FastAPI dependencies: a DB session per request, the signed-in user, their schools."""

from fastapi import Depends, Header, HTTPException

from ti import auth, db
from ti.db import User


def get_db():
    s = db.session()
    try:
        yield s
    finally:
        s.close()


def current_user(authorization: str = Header(default=""), s=Depends(get_db)) -> User:
    tok = authorization.removeprefix("Bearer ").strip()
    uid = auth.user_id_from(tok) if tok else None
    user = s.get(User, uid) if uid else None
    if user is None:
        raise HTTPException(401, "Sign in again")
    return user


def scope(user: User = Depends(current_user), s=Depends(get_db)):
    return auth.school_ids(s, user)


def manager(user: User = Depends(current_user)) -> User:
    if user.role != "manager":
        raise HTTPException(403, "Only the programme manager can do this")
    return user


def planner(user: User = Depends(current_user)) -> User:
    if user.role not in ("manager", "supervisor"):
        raise HTTPException(403, "Only the programme manager or a supervisor can do this")
    return user
