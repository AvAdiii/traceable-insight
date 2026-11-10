"""The HRS Project Champion assessment template: which header means which field.

Headers are matched loosely (case, spacing, the template's own spellings such as
"Broard Jump" and "Edurance"), so a trainer's small edits to a header still load.
"""

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Test:
    key: str
    label: str            # short, for UI
    full: str             # as the coordinator says it
    unit: str
    skill: str            # jump | throw | run | endurance | body
    lower_is_better: bool
    lo: float             # plausible range for school children
    hi: float


TESTS = {
    "jump": Test("jump", "Broad jump", "Standing broad jump", "m", "jump", False, 0.2, 3.2),
    "shuttle": Test("shuttle", "Shuttle run", "Shuttle run 4×10 m", "s", "run", True, 7.0, 40.0),
    "ball": Test("ball", "Ball throw", "1 kg medicine ball throw", "m", "throw", False, 0.3, 12.0),
    "relay": Test("relay", "Relay endurance", "Relay run endurance challenge", "s", "endurance",
                  True, 6.0, 120.0),
}
BODY = {
    "height": Test("height", "Height", "Height", "cm", "body", False, 85.0, 195.0),
    "weight": Test("weight", "Weight", "Weight", "kg", "body", False, 12.0, 110.0),
    "bmi": Test("bmi", "BMI", "Body mass index", "kg/m²", "body", False, 9.0, 40.0),
}
ALL = {**TESTS, **BODY}
SKILLS = {"jump": "jump", "throw": "ball", "run": "shuttle", "endurance": "relay"}

# field -> regex over a normalised header
HEADERS = {
    "school": r"name of (the )?school|^school",
    "klass": r"^class|^grade|^std",
    "name": r"student name|child name|^name$|name of (the )?(student|child)",
    "parent": r"parent|father|mother|guardian",
    "dob": r"^dob|date of birth|birth",
    "weight": r"^weight",
    "height": r"^height",
    "bmi": r"^bmi",
    "jump": r"b[ro]+a?r?d jump|long jump|standing jump",
    "shuttle": r"shuttle",
    "ball": r"medicine|ball throw|med ball",
    "relay": r"relay|edurance challenge|endurance challenge",
    "gender": r"gender|^sex|boys.?girls",
    "running": r"^running$",
    "agility": r"^agility$",
    "endurance": r"^endurance$",
}
REQUIRED = {"school", "name", "klass"}


def norm_header(h) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", str(h or "").lower())).strip()


def map_headers(row: list) -> dict[str, int]:
    """Header cells -> {field: column index}. First match wins for each field."""
    out: dict[str, int] = {}
    for i, h in enumerate(row):
        n = norm_header(h)
        if not n:
            continue
        for field, pat in HEADERS.items():
            if field not in out and re.search(pat, n):
                out[field] = i
                break
    return out


def is_template(cols: dict[str, int]) -> bool:
    return REQUIRED <= cols.keys() and any(t in cols for t in TESTS)


CLASS_ORDER = ["Nursery", "LKG", "UKG", "Class I", "Class II", "Class III", "Class IV",
               "Class V", "Class VI", "Class VII", "Class VIII", "Class IX", "Class X"]
_ROMAN = {"i": 1, "ii": 2, "iii": 3, "iv": 4, "v": 5, "vi": 6, "vii": 7, "viii": 8, "ix": 9,
          "x": 10}
_NUM_ROMAN = {v: k.upper() for k, v in _ROMAN.items()}


def norm_class(v) -> str:
    s = str(v or "").strip()
    m = re.search(r"\b(x|ix|viii|vii|vi|v|iv|iii|ii|i|10|[1-9])\b", s.lower().replace("class", " "))
    if not m:
        return s
    tok = m.group(1)
    n = int(tok) if tok.isdigit() else _ROMAN[tok]
    return f"Class {_NUM_ROMAN[n]}"


def class_number(k: str) -> int | None:
    m = re.search(r"Class ([IVX]+)$", k or "")
    return _ROMAN[m.group(1).lower()] if m else None


def norm_gender(v) -> str:
    s = str(v or "").strip().lower()
    if s.startswith(("b", "m")):
        return "Boys"
    if s.startswith(("g", "f")):
        return "Girls"
    return ""
