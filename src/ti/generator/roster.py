"""Roster: the canonical list every other synthetic file is generated from."""

import random
from dataclasses import asdict, dataclass

import jellyfish

from ti.generator import names

COACH = "Coach Arjun Mehra"          # fictional
PE_TEACHER = "Lata Iyer (PE)"         # fictional
COORDINATOR = "Neha HRS"              # fictional
SCHOOL = "Gandhi Nagar Govt. High School (synthetic)"
N_CHILDREN = 25


@dataclass(frozen=True)
class Child:
    child_id: str
    first: str
    surname: str
    cls: str
    age: int
    gender: str

    @property
    def full(self) -> str:
        return f"{self.first} {self.surname}"

    def row(self) -> dict:
        d = asdict(self)
        d["class"] = d.pop("cls")
        return d


def _too_similar(name: str, taken: list[str]) -> bool:
    return any(jellyfish.jaro_winkler_similarity(name.lower(), t.lower()) > 0.8 for t in taken)


def build_roster(rng: random.Random) -> list[Child]:
    """25 children with distinct first names except the deliberate Ravi pair."""
    people: list[tuple[str, str, str]] = [(f, s, "M") for f, s in names.RAVI_PAIR]
    taken = ["Ravi"]
    pool = [(f, "M") for f in names.FIRST_BOYS] + [(f, "F") for f in names.FIRST_GIRLS]
    rng.shuffle(pool)
    for first, gender in pool:
        if len(people) == N_CHILDREN:
            break
        if _too_similar(first, taken):
            continue
        taken.append(first)
        people.append((first, rng.choice(names.SURNAMES), gender))
    rng.shuffle(people)
    roster = []
    for i, (first, surname, gender) in enumerate(people, 1):
        cls = "6" if i % 2 else "7"
        age = (11 if cls == "6" else 12) + rng.choice([0, 0, 1])
        roster.append(Child(f"A{i:02d}", first, surname, cls, age, gender))
    return roster
