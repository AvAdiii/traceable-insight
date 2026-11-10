"""Passwords (scrypt) and signed tokens (JWT). Roles scope which schools a user sees.

manager     every school
supervisor  schools they supervise
trainer     schools they train (can upload for them)
"""

import base64
import datetime as dt
import hashlib
import hmac
import os

import jwt
from sqlalchemy import or_, select

from ti import config
from ti.db import School, User


def hash_password(pw: str) -> str:
    salt = os.urandom(16)
    h = hashlib.scrypt(pw.encode(), salt=salt, n=2**14, r=8, p=1)
    return "scrypt$" + base64.b64encode(salt).decode() + "$" + base64.b64encode(h).decode()


def check_password(pw: str, stored: str) -> bool:
    try:
        _, salt, h = stored.split("$")
        got = hashlib.scrypt(pw.encode(), salt=base64.b64decode(salt), n=2**14, r=8, p=1)
        return hmac.compare_digest(got, base64.b64decode(h))
    except (ValueError, TypeError):
        return False


def token(user: User) -> str:
    exp = dt.datetime.now(dt.UTC) + dt.timedelta(hours=config.TOKEN_HOURS)
    return jwt.encode({"sub": str(user.id), "role": user.role, "exp": exp}, config.SECRET,
                      algorithm="HS256")


def user_id_from(tok: str) -> int | None:
    try:
        return int(jwt.decode(tok, config.SECRET, algorithms=["HS256"])["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        return None


def school_ids(s, user: User) -> set[str] | None:
    """None means all schools."""
    if user.role == "manager":
        return None
    rows = s.scalars(select(School.id).where(
        or_(School.supervisor_id == user.id, School.trainer_id == user.id)))
    return set(rows)
