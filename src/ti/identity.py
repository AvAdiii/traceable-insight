"""Who is who across rounds: link a spreadsheet row to one child in the registry.

Indian school registers write the same child as "Komire Umesh", "K.Umesh" or "Umesh K", and
"Md."/"Mohd."/"Mohammed" interchangeably. Matching is order-insensitive and initials-aware, and
uses parent name and date of birth as tie-breakers. A row links only when one child is a clear
winner; anything close goes to the Inbox as "Name to confirm".

Within one round two different rows are never fuzzily merged: twins like "Gurram Shashank" and
"Gurram Sushant" share a parent and DOB. Fuzzy matching only looks at children already known from
other rounds who have no row yet in this round.
"""

import re

import jellyfish
from rapidfuzz import fuzz

LINK_MIN = 90.0
LINK_LEAD = 6.0
REVIEW_MIN = 74.0

_ALIASES = {
    "md": "md", "mohd": "md", "mohammed": "md", "mohammad": "md", "mohmmed": "md", "mohamed": "md",
    "muhammad": "md", "mohd.": "md", "sk": "sk", "shaik": "sk", "shaikh": "sk", "syed": "sy",
    "sd": "sy", "sri": "sri", "shri": "sri", "sree": "sri",
}


def tokens(s: str) -> list[str]:
    out = []
    for t in re.split(r"[^a-z]+", (s or "").lower()):
        if t:
            out.append(_ALIASES.get(t, t))
    return out


def _tok_sim(a: str, b: str) -> float:
    if a == b:
        return 100.0
    if len(a) == 1 or len(b) == 1:
        return 100.0 if a[0] == b[0] else 0.0
    s = max(100 * jellyfish.jaro_winkler_similarity(a, b), fuzz.ratio(a, b))
    if len(a) > 3 and jellyfish.metaphone(a) == jellyfish.metaphone(b):
        s = max(s, 93.0)
    return s


def name_sim(a: str, b: str) -> float:
    """0-100. Every full word of the shorter name must find a strong partner."""
    ta, tb = tokens(a), tokens(b)
    if not ta or not tb:
        return 0.0
    if "".join(ta) == "".join(tb):            # "SriChitanya" vs "Sri Chitanya"
        return 100.0
    if len(ta) > len(tb):
        ta, tb = tb, ta
    left = list(tb)
    total = weight = 0.0
    weakest = 100.0
    for t in ta:
        best_i, best = None, -1.0
        for i, u in enumerate(left):
            s = _tok_sim(t, u)
            if s > best:
                best_i, best = i, s
        w = 0.5 if len(t) == 1 else float(len(t))
        total += best * w
        weight += w
        if len(t) > 1:
            weakest = min(weakest, best)
        if best_i is not None:
            left.pop(best_i)
    score = total / weight
    score *= 0.93 ** sum(1 for u in left if len(u) > 1)    # extra full words in the longer name
    if weakest < 86:
        score = min(score, 70.0)
    if "".join(ta) and len(ta) == 1 and len(ta[0]) == 1:
        score = min(score, 40.0)
    return round(score, 1)


def dob_sim(a, b) -> float:
    if not a or not b:
        return 60.0
    if a == b:
        return 100.0
    if a.day == b.month and a.month == b.day and a.year == b.year:   # day/month swapped
        return 80.0
    if abs((a - b).days) <= 31:
        return 60.0
    return 0.0


def score(row, child) -> float:
    n = name_sim(row.name, child.name)
    p = name_sim(row.parent, child.parent) if row.parent and child.parent else 70.0
    return round(0.65 * n + 0.2 * p + 0.15 * dob_sim(row.dob, child.dob), 1)


def exact_key(school_id, name, parent, dob) -> tuple:
    return (school_id, " ".join(sorted(tokens(name))), " ".join(sorted(tokens(parent))),
            dob.isoformat() if dob else "")


def best_match(row, candidates) -> tuple[str, object, float, list]:
    """-> (status, child, score, [(child_id, score)]) where status is fuzzy | review | new."""
    scored = sorted(((score(row, c), c) for c in candidates
                     if not row.gender or not c.gender or row.gender == c.gender),
                    key=lambda x: -x[0])
    cands = [(c.id, s) for s, c in scored[:3]]
    if not scored:
        return "new", None, 0.0, []
    top, c = scored[0]
    second = scored[1][0] if len(scored) > 1 else 0.0
    if top >= LINK_MIN and top - second >= LINK_LEAD:
        return "fuzzy", c, top, cands
    if top >= REVIEW_MIN:
        return "review", None, top, cands
    return "new", None, top, cands
