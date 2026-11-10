"""Turn one raw cell into a value with a status and a reason. Never guesses silently.

ok        read as written
repaired  a typing slip was fixed (raw kept, reason given), counted
suspect   readable but implausible or a placeholder; excluded from rankings until accepted
missing   blank, zero or unreadable
"""

import datetime as dt
import re
from dataclasses import dataclass

from ti.template import ALL


@dataclass
class Clean:
    value: float | None
    status: str
    note: str = ""


def raw_text(v) -> str:
    if v is None:
        return ""
    if isinstance(v, dt.datetime):
        return v.strftime("%Y-%m-%d") if v.time() == dt.time() else v.isoformat(sep=" ")
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    return str(v).strip()


_EXCEL_EPOCH = dt.datetime(1899, 12, 30)


def number(v, field: str) -> Clean:
    """Parse a test cell. Range checks happen here; placeholder checks need the whole file."""
    if v is None or (isinstance(v, str) and not v.strip()):
        return Clean(None, "missing", "Blank cell")
    t = ALL[field]
    if isinstance(v, (dt.datetime, dt.date)):
        # A number Excel auto-formatted as a date (e.g. 2.5 shown as 02-01-1900 12:00).
        d = v if isinstance(v, dt.datetime) else dt.datetime.combine(v, dt.time())
        if d.year < 1901:
            # Excel's 1900 date system: serials before 1 Mar 1900 count from 31 Dec 1899.
            epoch = dt.datetime(1899, 12, 31) if d < dt.datetime(1900, 3, 1) else _EXCEL_EPOCH
            x = round((d - epoch).total_seconds() / 86400, 2)
            return _range(Clean(x, "repaired", f"Excel showed this number as a date; read as {x:g}"), t)
        return Clean(None, "missing", "A date in a number column")
    if isinstance(v, (int, float)):
        x = float(v)
        if x == 0:
            return Clean(None, "missing", "Zero entered; treated as not tested")
        return _range(Clean(x, "ok"), t)
    s = str(v).strip()
    try:
        x = float(s)
        if x == 0:
            return Clean(None, "missing", "Zero entered; treated as not tested")
        return _range(Clean(x, "ok"), t)
    except ValueError:
        pass
    fixed = re.sub(r"\.{2,}", ".", s)                 # 5..84
    fixed = re.sub(r"^[.,]+(?=\d)", "", fixed)        # .12.25 (stray leading dot)
    fixed = fixed.replace(",", ".")
    fixed = re.sub(r"(?<=\d)\s*[a-zA-Z]+$", "", fixed)  # 17kh, 1.2m
    if re.fullmatch(r"\d+(\.\d+)?", fixed):
        x = float(fixed)
        return _range(Clean(x, "repaired", f"Typed as “{s}”; read as {x:g}"), t)
    return Clean(None, "missing", f"Could not read “{s}”")


def _range(c: Clean, t) -> Clean:
    if c.value is None:
        return c
    if c.value < t.lo or c.value > t.hi:
        hint = unit_hint(t.key, c.value)
        note = f"{c.value:g} {t.unit} is outside the usual {t.lo:g}–{t.hi:g} {t.unit}"
        if hint:
            note += f"; {hint[1]}"
        return Clean(c.value, "suspect", (c.note + ". " if c.note else "") + note)
    return c


def unit_hint(field: str, x: float) -> tuple[float, str] | None:
    """A likely corrected value when a number looks like the wrong unit."""
    if field == "jump":
        if x >= 40:
            return round(x / 100, 2), f"looks like centimetres ({x / 100:.2f} m)"
        if 3.2 < x <= 11:
            return round(x * 0.3048, 2), f"looks like feet ({x * 0.3048:.2f} m)"
        if 11 < x < 40:
            return round(x / 10, 2), f"looks like a slipped decimal ({x / 10:.2f} m)"
    if field == "height":
        if x < 3:
            return round(x * 100, 1), f"looks like metres ({x * 100:.0f} cm)"
        if x < 85:
            return None
    if field == "ball" and x > 12:
        return round(x / 10, 2), f"looks like a slipped decimal ({x / 10:.2f} m)"
    return None


_DOB_FORMATS = ["%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y", "%d/%m/%y", "%d-%m-%y", "%Y-%m-%d"]


def dob(v) -> tuple[dt.date | None, str]:
    """(date, note). Note is non-empty when the cell needed care or failed."""
    if v is None or (isinstance(v, str) and not v.strip()):
        return None, "Blank date of birth"
    if isinstance(v, dt.datetime):
        return v.date(), ""
    if isinstance(v, dt.date):
        return v, ""
    if isinstance(v, (int, float)) and 1000 < v < 60000:
        return (_EXCEL_EPOCH + dt.timedelta(days=float(v))).date(), ""
    s = str(v).strip()
    for f in _DOB_FORMATS:
        try:
            return dt.datetime.strptime(s, f).date(), ""
        except ValueError:
            pass
    digits = re.sub(r"\D", "", s)
    if len(digits) == 8:                                  # 07/022019
        try:
            return dt.datetime.strptime(digits, "%d%m%Y").date(), f"Read “{s}” as {digits[:2]}/{digits[2:4]}/{digits[4:]}"
        except ValueError:
            pass
    return None, f"Could not read date of birth “{s}”"


def age_on(birth: dt.date | None, on: dt.date) -> float | None:
    if not birth:
        return None
    a = (on - birth).days / 365.25
    return round(a, 2) if 3 <= a <= 20 else None


def name_key(s: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z ]", " ", (s or "").lower())).strip()
