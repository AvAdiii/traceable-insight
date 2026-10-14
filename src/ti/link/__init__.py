"""A4 link: map a written name to one roster child, or send it to the review queue.

A mention links only when one child is a clear winner. Anything close but uncertain,
including a first name two children share, goes to the coordinator's review queue.
"""

import re
from dataclasses import dataclass, field

import jellyfish
from rapidfuzz import fuzz

LINK_MIN = 90.0
LINK_LEAD = 8.0
REVIEW_MIN = 75.0
GROUP = re.compile(r"\b(class|boys|girls|sab|all|team|bacche|bachon)\b", re.I)


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z ]", " ", s.lower())).strip()


def _sim(a: str, b: str) -> float:
    """0-100 similarity of two single name tokens, tolerant of typing slips."""
    if a == b:
        return 100.0
    s = max(100 * jellyfish.jaro_winkler_similarity(a, b), fuzz.ratio(a, b))
    if len(a) > 2 and jellyfish.metaphone(a) == jellyfish.metaphone(b):
        s = max(s, 92.0)
    return s


@dataclass
class MatchResult:
    status: str                      # linked | review | unlinked | skipped
    child_id: str | None
    score: float
    candidates: list = field(default_factory=list)   # [(child_id, score)] best first


class Matcher:
    def __init__(self, roster: list[dict]):
        self.roster = [(c["child_id"], norm(c["first"]), norm(c["surname"])) for c in roster]

    def score(self, surface: str, first: str, surname: str) -> float:
        toks = norm(surface).split()
        if not toks:
            return 0.0
        if len(toks) == 1:
            t = toks[0]
            return max(_sim(t, first), _sim(t, (first + surname).replace(" ", "")))
        f, rest = toks[0], "".join(toks[1:])
        first_s = _sim(f, first)
        if len(rest) == 1:                       # "Ravi K" / "Ravi K."
            last_s = 100.0 if surname.startswith(rest) else 0.0
        else:
            last_s = _sim(rest, surname.replace(" ", ""))
        return 0.6 * first_s + 0.4 * last_s

    def match(self, surface: str) -> MatchResult:
        if GROUP.search(surface) or len(norm(surface)) < 3:
            return MatchResult("skipped", None, 0.0)
        scored = sorted(((round(self.score(surface, f, s), 1), cid)
                         for cid, f, s in self.roster), reverse=True)
        cands = [(cid, sc) for sc, cid in scored[:3]]
        top, second = scored[0][0], scored[1][0] if len(scored) > 1 else 0.0
        if top >= LINK_MIN and top - second >= LINK_LEAD:
            return MatchResult("linked", scored[0][1], top, cands)
        if top >= REVIEW_MIN:
            return MatchResult("review", None, top, cands)
        return MatchResult("unlinked", None, top, cands)
