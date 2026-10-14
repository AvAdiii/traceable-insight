import pytest

from ti.link import Matcher

ROSTER = [
    {"child_id": "A03", "first": "Ravi", "surname": "Kumar"},
    {"child_id": "A13", "first": "Ravi", "surname": "Shankar"},
    {"child_id": "A04", "first": "Omana", "surname": "Mishra"},
    {"child_id": "A02", "first": "Priya", "surname": "Menon"},
    {"child_id": "A07", "first": "Lakshmi", "surname": "Menon"},
    {"child_id": "A18", "first": "Siddharth", "surname": "Khan"},
    {"child_id": "A24", "first": "Bharat", "surname": "Iyer"},
]


@pytest.mark.parametrize("surface,child", [
    ("Ravi K", "A03"), ("Ravi K.", "A03"), ("Ravikumar", "A03"), ("Ravi Shankar", "A13"),
    ("Omanaa", "A04"), ("omana", "A04"), ("Priya M", "A02"), ("Siddharth", "A18"),
    ("Bharat I", "A24"), ("Lakshmi Menon", "A07"),
])
def test_links_variants(surface, child):
    r = Matcher(ROSTER).match(surface)
    assert (r.status, r.child_id) == ("linked", child), r


def test_shared_first_name_goes_to_review():
    r = Matcher(ROSTER).match("ravi")
    assert r.status == "review" and {c for c, _ in r.candidates[:2]} == {"A03", "A13"}


def test_group_reference_skipped():
    assert Matcher(ROSTER).match("Class 6 boys").status == "skipped"


def test_stranger_unlinked():
    assert Matcher(ROSTER).match("Neha").status == "unlinked"
