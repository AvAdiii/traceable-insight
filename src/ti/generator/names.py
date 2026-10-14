"""Common Indian first names and surnames (public, generic lists) and name-variant rules."""

import random

FIRST_BOYS = [
    "Aarav", "Ajay", "Vikram", "Rohan", "Karthik", "Siddharth", "Manoj", "Imran",
    "Harish", "Naveen", "Tarun", "Deepak", "Suresh", "Farhan", "Gopal", "Yusuf",
    "Bharat", "Lokesh", "Pranav", "Zubair",
]
FIRST_GIRLS = [
    "Ananya", "Priya", "Sneha", "Kavya", "Meena", "Divya", "Lakshmi", "Fatima",
    "Nandini", "Pooja", "Swathi", "Harini", "Ishita", "Bhavana", "Tanvi", "Rukhsar",
    "Gayathri", "Sahana", "Jyothi", "Omana",
]
SURNAMES = [
    "Reddy", "Sharma", "Naidu", "Rao", "Patel", "Khan", "Iyer", "Verma", "Gupta",
    "Pillai", "Yadav", "Chowdary", "Goud", "Ali", "Menon", "Joshi", "Shaikh", "Varma",
    "Mishra", "Nair",
]

# The shared-first-name pair is fixed so the demo case is always present.
RAVI_PAIR = [("Ravi", "Kumar"), ("Ravi", "Shankar")]

NICKNAMES = {
    "Vikram": "Vicky", "Siddharth": "Sid", "Pranav": "Pranu", "Lakshmi": "Lucky",
    "Gayathri": "Gayu", "Karthik": "Karthi", "Nandini": "Nandu", "Bhavana": "Bhavi",
}


def misspell(first: str, rng: random.Random) -> str:
    """A plausible typing slip: doubled final vowel, dropped 'h', or i/ee swap."""
    options = []
    if first[-1] in "aiu":
        options.append(first + first[-1])
    if "h" in first[1:]:
        i = first.index("h", 1)
        options.append(first[:i] + first[i + 1:])
    if "i" in first[1:]:
        options.append(first[0] + first[1:].replace("i", "ee", 1))
    return rng.choice(options) if options else first + "a"


def variants(first: str, surname: str, rng: random.Random, formal: bool = False) -> list[str]:
    """Non-canonical ways a coach or teacher writes this child's name.

    The shared first name never gets a first-name-only variant: those are planted
    separately as deliberately ambiguous mentions. Formal sheets (attendance, assessments)
    get initials and typing slips, never nicknames or lowercase first names.
    """
    out = [f"{first} {surname[0]}", f"{first} {surname[0]}."]
    if first == "Ravi":
        return out + [f"Ravi{surname.lower()}"]  # e.g. "Ravikumar"
    if formal:
        return out + [misspell(first, rng) + " " + surname]
    out += [first.lower(), misspell(first, rng)]
    if first in NICKNAMES:
        out.append(NICKNAMES[first])
    return out


def surface(first: str, surname: str, rng: random.Random, rate: float = 0.2,
            formal: bool = False) -> str:
    """How a child's name is written in one mention: usually plain, sometimes a variant."""
    if rng.random() < rate:
        return rng.choice(variants(first, surname, rng, formal))
    if formal or first == "Ravi":
        return f"{first} {surname}"
    return first
