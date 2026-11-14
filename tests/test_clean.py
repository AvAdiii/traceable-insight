import datetime as dt

from ti import clean
from ti.template import map_headers, norm_class, norm_gender


def test_typos_are_repaired_and_explained():
    assert clean.number("17kh", "weight").value == 17
    c = clean.number(".12.25", "shuttle")
    assert (c.value, c.status) == (12.25, "repaired")
    assert clean.number("5..84", "relay").value == 5.84
    assert clean.number(dt.datetime(1900, 1, 2, 12, 0), "ball").value == 2.5


def test_zero_and_blank_are_missing_not_values():
    assert clean.number(0, "shuttle").status == "missing"
    assert clean.number("", "jump").status == "missing"


def test_implausible_values_are_suspect_with_a_unit_hint():
    c = clean.number(155, "jump")
    assert c.status == "suspect" and "centimetres" in c.note
    assert clean.unit_hint("jump", 4.6)[0] == 1.4      # feet


def test_dob_formats():
    assert clean.dob("25/10/2019")[0] == dt.date(2019, 10, 25)
    d, note = clean.dob("07/022019")
    assert d == dt.date(2019, 2, 7) and note
    assert clean.dob("15/0620")[0] is None


def test_template_headers_with_the_partners_spellings():
    cols = map_headers(["Name of the School", "Class", "Student Name", "Parent Name", "DOB", "Weight",
                        "Height", "BMI", "Broard Jump Test(in meter)", "Shuttle Run 4x10(in Seconds)",
                        "1KG Medicine Ball Throw(in meter)", "Relay Run Edurance Challenge", "Gender"])
    assert {"school", "klass", "name", "jump", "shuttle", "ball", "relay", "gender"} <= cols.keys()
    assert norm_class("class 5") == "Class V" and norm_class("VIII") == "Class VIII"
    assert norm_gender("Girls") == "Girls" and norm_gender("M") == "Boys"
