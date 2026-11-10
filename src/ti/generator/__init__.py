"""Seeded synthetic Project Champion data on the exact HRS assessment template.

Eight fictional schools, three rounds (baseline, midline, endline of 2025-26). Every error type found
in the real HRS workbook is planted, with ground truth written next to the files:

- a whole school block entered twice (Sitara Nagar)
- one class block copy-pasted into another class (Kondapur, Class I -> Class III)
- placeholder values typed for most children (Ramnagar ball throw 2.5, Bapuji Nagar shuttle 16)
- relay recorded as levels (3 / 5) instead of seconds in one school
- wrong units (jump in feet, jump in cm), height typos, zeros, typing slips ("17kh", ".12.25",
  "5..84"), a number Excel turned into a date, malformed and placeholder dates of birth
- a "Revised Data" sheet that drops columns and disagrees with Sheet1 in a few cells
- name variants across rounds ("Komire Umesh" -> "K.Umesh"), twins, and conflicting duplicates

Nothing here is real. Names are random combinations; schools are invented.
"""

import datetime as dt
import json
import math
import random
from dataclasses import dataclass, field
from pathlib import Path

import openpyxl
from openpyxl.styles import Font, PatternFill

HEADERS_S1 = ["Name of the School", "Class", "Student Name", "Parent Name", "DOB", "Weight",
              "Height", "BMI", "Broard Jump Test(in meter)", "Shuttle Run 4x10(in Seconds)",
              "1KG Medicine Ball Throw(in meter)", "Relay Run Edurance Challenge", "Gender",
              "Running", "Agility", "Endurance"]
HEADERS_REV = ["Name of the School", "Class", "Student Name", "Parent Name", "DOB", "Weight",
               "Height", "BMI", "Broard Jump Test(in meter)", "Shuttle Run 4x10(in Seconds)",
               "1KG Medicine Ball Throw(in meter)", "Gender"]

ROMAN = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X"]

SCHOOLS = [
    # name, short, area, classes, size, girls_only
    ("Sitara Nagar Primary School", "Sitara Nagar", "Shaikpet mandal", range(1, 6), 210, False),
    ("MRC Kondapur Primary School", "Kondapur", "Serilingampally", range(1, 6), 150, False),
    ("Ramnagar Upper Primary School", "Ramnagar", "Musheerabad", range(6, 11), 170, False),
    ("Zilla Parishad High School, Lingampally", "ZPHS Lingampally", "Lingampally", range(6, 11), 240, False),
    ("Bapuji Nagar Primary School", "Bapuji Nagar", "Secunderabad", range(1, 6), 150, False),
    ("MPUPS Moosapet", "Moosapet", "Kukatpally", range(1, 8), 170, False),
    ("GGHS Old City", "GGHS Old City", "Charminar", range(1, 11), 150, True),
    ("NATCO Erragadda Primary School", "Erragadda", "Erragadda", range(1, 6), 190, False),
]

ROUNDS = [("baseline", "Baseline 2025-26", dt.date(2025, 7, 15)),
          ("midline", "Midline 2025-26", dt.date(2025, 11, 20)),
          ("endline", "Endline 2025-26", dt.date(2026, 2, 24))]

BOYS = ("Shashank Sushant Umesh Rishith Rahul Karthik Kiran Vijay Mohan Harikrishna Akhil Praveen "
        "Ravi Varun Balaji Vishal Ruthvik Raghavendra Prabhukiran Moses Vishnu Rajesh Srivardhan "
        "Chetan Naveen Arshith Likhith Durgesh Nashanth Akash Abhiram Yashwanth Charan Manikanta "
        "Harsha Ganesh Arjun Teja Sathvik Rohith Lokesh Nikhil Pavan Sandeep Bharath Hemanth").split()
GIRLS = ("Rishitha Deepika Jhansi Samitha Rushika Nandhitha Bhavani Bhoomika Bindu Swathika "
         "Keerthana Vaishnavi Mounika Anusha Bhargavi Yamuna Ashwija Rajitha Harini Lasya Sahithi "
         "Varshitha Tejaswini Pravalika Sneha Pooja Meghana Akshaya Hasini Sravani Divya Navya "
         "Kavya Srija Manasa Likitha Sowmya Ramya Pallavi Shirisha").split()
M_BOYS = "Zaid Imran Faizan Sameer Ayaan Adnan Junaid Sohail Arbaz Rehan Zian Hasfar".split()
M_GIRLS = "Amreen Nigar Sana Ayesha Fathima Aisha Amyra Mahek Zoya Afreen Heena Rubina".split()
SURNAMES = ("Gurram Komire Ramavath Vastrala Chauhan Kethavath Bollam Pittala Gaddam Erukala "
            "Madishetty Peddi Banoth Jatoth Dasari Kuruva Thota Yadav Goud Naik Bandari Kommu "
            "Chilukuri Mekala Bairi Pasula Talari Vadla Neelam Dodla").split()
FATHERS = ("Shivakumar Bhaskar Raju Balraj Srinivas Ramesh Venkatesh Mahesh Narsing Prem Kumar "
           "Yadagiri Mallesh Anjaiah Krishna Suresh Ravinder Sailu Ramulu Narsimha Kumar").split()
M_FATHERS = "Ismail Moula Ramjani Khaja Saleem Rafiq Yousuf Anwar Jaleel Hussain".split()


@dataclass
class Kid:
    tid: str
    school: int
    klass: int
    gender: str
    given: str
    surname: str
    muslim: bool
    father: str
    dob: dt.date
    style: str
    z: float
    zs: dict
    trend: float
    absent: set = field(default_factory=set)
    joins: int = 0


def display_name(k: Kid, style: str) -> str:
    g, s = k.given, k.surname
    if k.muslim:
        pre = "Md." if k.gender == "Boys" else "Sk."
        return {"full": f"{'Mohammed' if k.gender == 'Boys' else 'Shaik'} {g}",
                "init": f"{pre}{g}", "given": g, "rev": f"{g} {pre.rstrip('.')}",
                "lower": f"{pre.lower()}{g.lower()}"}.get(style, f"{pre}{g}")
    return {"full": f"{s} {g}", "init": f"{s[0]}.{g}", "given": g, "rev": f"{g} {s[0]}",
            "lower": f"{s.lower()} {g.lower()}"}[style]


def parent_name(k: Kid) -> str:
    if k.muslim:
        return f"Md. {k.father}" if k.tid[-1] in "02468" else f"Mohammed {k.father}"
    return f"{k.surname} {k.father}"


def typo(rng: random.Random, s: str) -> str:
    i = rng.randrange(1, max(2, len(s) - 1))
    ops = [lambda: s[:i] + s[i + 1:], lambda: s[:i] + s[i] + s[i:],
           lambda: s[:i] + {"a": "e", "i": "l", "e": "a", "o": "u"}.get(s[i], s[i]) + s[i + 1:]]
    return rng.choice(ops)()


def _kids(rng: random.Random) -> list[Kid]:
    kids, n = [], 0
    for si, (_, _, _, classes, size, girls_only) in enumerate(SCHOOLS):
        per = size // len(classes)
        for c in classes:
            for _ in range(per + rng.randint(-4, 4)):
                n += 1
                gender = "Girls" if girls_only or rng.random() < 0.48 else "Boys"
                muslim = rng.random() < (0.35 if si in (6, 0) else 0.12)
                if muslim:
                    given = rng.choice(M_BOYS if gender == "Boys" else M_GIRLS)
                    if gender == "Girls" and rng.random() < 0.3:
                        given += rng.choice([" Begum", " Anjum", " Fatima"])
                    surname, father = "", rng.choice(M_FATHERS)
                else:
                    given = rng.choice(BOYS if gender == "Boys" else GIRLS)
                    surname, father = rng.choice(SURNAMES), rng.choice(FATHERS)
                age = c + 5 + rng.uniform(0.0, 1.0)
                dob = ROUNDS[0][2] - dt.timedelta(days=int(age * 365.25))
                z = rng.gauss(0, 1)
                zs = {t: 0.65 * z + 0.76 * rng.gauss(0, 1) for t in ("jump", "shuttle", "ball", "relay")}
                trend = rng.gauss(0.22, 0.3)
                if rng.random() < 0.08:
                    trend = rng.uniform(-0.9, -0.45)       # a real decline
                style = rng.choices(["full", "init", "given", "rev", "lower"], [40, 36, 10, 9, 5])[0]
                kids.append(Kid(f"T{n:04d}", si, c, gender, given, surname, muslim, father, dob,
                                style, z, zs, trend))
        # twins: same parent and DOB, similar names
        same = [k for k in kids if k.school == si and k.gender == "Boys" and not k.muslim]
        if len(same) > 4:
            a = same[1]
            n += 1
            kids.append(Kid(f"T{n:04d}", si, a.klass, "Boys", "Sushant" if a.given != "Sushant" else "Shashank",
                            a.surname, False, a.father, a.dob, a.style, a.z, dict(a.zs), a.trend))
    for k in kids:
        if rng.random() < 0.04:
            k.absent.add(rng.choice([1, 2]))
        if rng.random() < 0.03:
            k.joins = 1
    return kids


def measures(k: Kid, r: int, on: dt.date, rng: random.Random) -> dict:
    a = (on - k.dob).days / 365.25
    girl = k.gender == "Girls"
    zz = {t: v + r * k.trend + rng.gauss(0, 0.18) for t, v in k.zs.items()}
    jump = (0.45 + 0.09 * (a - 5)) * (0.93 if girl else 1) + zz["jump"] * 0.13 * (1 + 0.04 * (a - 5))
    shuttle = max(10.4, 21.5 - 0.72 * (a - 5) + (0.9 if girl else 0)) - zz["shuttle"] * 1.35
    ball = (1.0 + 0.27 * (a - 5)) * (0.86 if girl else 1) + zz["ball"] * 0.27 * (1 + 0.05 * (a - 5))
    relay = 26 - 0.9 * (a - 5) + (1.2 if girl else 0) - zz["relay"] * 2.1
    h = 108 + 6.1 * (a - 5) + rng.gauss(0, 5) + 0.8 * r
    w = max(13, 17.5 + 2.5 * (a - 5) + rng.gauss(0, 3) + 0.3 * r)
    return {"weight": round(w), "height": round(h), "bmi": round(w / (h / 100) ** 2, 1),
            "jump": round(max(0.3, jump), 2), "shuttle": round(max(8.5, shuttle), 2),
            "ball": round(max(0.4, ball), 2), "relay": round(max(7.5, relay), 2)}


def _dob_cell(rng: random.Random, d: dt.date):
    x = rng.random()
    if x < 0.03:
        return dt.datetime(d.year, 1, 1)                      # placeholder 1 Jan
    if x < 0.62:
        return dt.datetime(d.year, d.month, d.day)
    return d.strftime("%d/%m/%Y")


def generate(out: Path, seed: int = 42) -> dict:
    rng = random.Random(seed)
    kids = _kids(rng)
    out.mkdir(parents=True, exist_ok=True)
    truth = {"seed": seed, "children": len(kids), "files": {}, "planted": []}
    dob_cells = {k.tid: _dob_cell(rng, k.dob) for k in kids}
    names = {k.tid: display_name(k, k.style) for k in kids}
    parents = {k.tid: parent_name(k) for k in kids}
    for r, (kind, label, on) in enumerate(ROUNDS):
        rows = []   # (kid, values-dict, overrides)
        for k in kids:
            if r in k.absent or (k.joins and r == 0):
                continue
            v = measures(k, r, on, rng)
            for t in ("jump", "shuttle", "ball", "relay"):
                if rng.random() < 0.025:
                    v[t] = None
            rows.append([k, v])
        if r > 0:   # names drift between rounds
            for k in kids:
                if rng.random() < 0.15:
                    names[k.tid] = display_name(k, rng.choice(["full", "init", "given", "rev"]))
                elif rng.random() < 0.025:
                    names[k.tid] = typo(rng, names[k.tid])
                if rng.random() < 0.03:
                    parents[k.tid] = typo(rng, parents[k.tid])
        truth_rows = _plant(rng, r, rows, truth)
        fname = f"PC_Assessment_{kind.title()}_{on:%Y-%m}.xlsx"
        _write(out / fname, r, rows, names, parents, dob_cells, rng, truth, fname)
        truth["files"][fname] = {"round": label, "kind": kind, "test_date": on.isoformat(),
                                 "rows": truth_rows}
    (out / "ground_truth.json").write_text(json.dumps(truth, indent=1, default=str))
    return truth


def _plant(rng, r, rows, truth) -> int:
    by_school = {}
    for row in rows:
        by_school.setdefault(row[0].school, []).append(row)
    p = truth["planted"]
    if r == 0:
        for row in by_school[2]:          # Ramnagar placeholder ball 2.5
            if rng.random() < 0.7:
                row[1]["ball"] = 2.5
        p.append({"round": r, "kind": "placeholder", "school": SCHOOLS[2][0], "field": "ball", "value": 2.5})
        for row in by_school[4]:          # Bapuji Nagar placeholder shuttle 16
            if rng.random() < 0.32:
                row[1]["shuttle"] = 16
        p.append({"round": r, "kind": "placeholder", "school": SCHOOLS[4][0], "field": "shuttle", "value": 16})
        for row in by_school[1]:          # Kondapur class I jump in feet
            if row[0].klass == 1 and row[1]["jump"]:
                row[1]["jump"] = round(row[1]["jump"] * 3.28, 1)
        p.append({"round": r, "kind": "unit_feet", "school": SCHOOLS[1][0], "field": "jump", "class": "Class I"})
        for row in by_school[0]:          # Sitara relay as levels
            row[1]["relay"] = rng.choice([3, 5, 5, 3, 4])
        p.append({"round": r, "kind": "relay_levels", "school": SCHOOLS[0][0]})
        z = by_school[3]
        z[5][1]["jump"] = 155
        z[40][1]["jump"] = 15.5
        p.append({"round": r, "kind": "implausible", "tid": z[5][0].tid, "field": "jump"})
        p.append({"round": r, "kind": "implausible", "tid": z[40][0].tid, "field": "jump"})
        e = by_school[7]
        e[12][1]["height"], e[12][1]["bmi"] = 15, 1244.4
        p.append({"round": r, "kind": "implausible", "tid": e[12][0].tid, "field": "height"})
        for row in rng.sample(rows, 10):
            row[1]["shuttle"] = 0
        sample = rng.sample(rows, 6)
        sample[0][1]["weight"] = f"{sample[0][1]['weight']}kh"
        sample[1][1]["shuttle"] = f".{sample[1][1]['shuttle']}"
        sample[2][1]["relay"] = str(sample[2][1]["relay"]).replace(".", "..")
        sample[3][1]["ball"] = dt.datetime(1900, 1, 2, 12, 0)
        sample[4][1]["_dob"] = "15/0620"
        sample[5][1]["_dob"] = "07/022019"
        p.append({"round": r, "kind": "typos", "tids": [s[0].tid for s in sample]})
    if r == 1:
        # conflicting duplicates: same child entered twice with different numbers
        for row in rng.sample(rows, 6):
            dup = dict(row[1])
            dup["shuttle"] = round((dup["shuttle"] or 15) + rng.uniform(1.5, 3.5), 2)
            row.append(dup)
            p.append({"round": r, "kind": "conflicting_duplicate", "tid": row[0].tid})
        bad = rng.choice(rows)
        bad[1]["ball"] = 21.0
        p.append({"round": r, "kind": "implausible", "tid": bad[0].tid, "field": "ball"})
    if r == 2:
        for row in rng.sample(rows, 25):
            row[1]["relay"] = None
    return len(rows)


def _write(path, r, rows, names, parents, dob_cells, rng, truth, fname):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Sheet1"
    ws.append(HEADERS_S1)
    for c in ws[1]:
        c.font = Font(bold=True)
        c.fill = PatternFill("solid", fgColor="FFF2CC")
    order = sorted(rows, key=lambda x: (x[0].school, x[0].klass, x[0].tid))
    out_rows = []
    for kid, v, *dups in order:
        for vals in [v, *dups]:
            out_rows.append((kid, vals))
    # Kondapur: Class I block pasted over Class III (planted in every round's file? only baseline)
    if r == 0:
        k1 = [(k, v) for k, v in out_rows if k.school == 1 and k.klass == 1]
        k3_idx = [i for i, (k, _) in enumerate(out_rows) if k.school == 1 and k.klass == 3]
        for j, i in enumerate(k3_idx[:len(k1)]):
            src_k, src_v = k1[j]
            vv = dict(src_v)
            vv["ball"] = round(rng.uniform(1.0, 2.4), 2)
            vv["_klass"] = 3
            out_rows[i] = (src_k, vv)
        truth["planted"].append({"round": 0, "kind": "class_copy", "school": SCHOOLS[1][0],
                                 "from": "Class I", "to": "Class III", "rows": len(k1)})
        # Sitara: whole school block entered again further down
        sit = [(k, v) for k, v in out_rows if k.school == 0]
        insert_at = next(i for i, (k, _) in enumerate(out_rows) if k.school == 5)
        out_rows[insert_at:insert_at] = sit
        truth["planted"].append({"round": 0, "kind": "duplicate_block", "school": SCHOOLS[0][0],
                                 "rows": len(sit)})
    row_truth = []
    rev = None
    if r == 0:
        rev = wb.create_sheet("Revised Data")
        rev.append(HEADERS_REV)
        for c in rev[1]:
            c.font = Font(bold=True)
    for i, (kid, v) in enumerate(out_rows, start=2):
        klass = v.get("_klass", kid.klass)
        dob = v.get("_dob", dob_cells[kid.tid])
        line = [SCHOOLS[kid.school][0], f"Class {ROMAN[klass - 1]}", names[kid.tid],
                parents[kid.tid], dob, v["weight"], v["height"], v["bmi"], v["jump"],
                v["shuttle"], v["ball"], v["relay"], kid.gender, None, None, None]
        ws.append(line)
        if isinstance(v["ball"], dt.datetime):
            ws.cell(i, 11).number_format = "dd-mm-yyyy hh:mm"
        row_truth.append({"row": i, "tid": kid.tid})
        if rev is not None:
            rl = line[:11] + [kid.gender]
            # The revised sheet fixes typing slips and, for a few rows, disagrees with Sheet1.
            for j in (5, 9, 10):
                if isinstance(rl[j], str) or isinstance(rl[j], dt.datetime):
                    rl[j] = None
            if rng.random() < 0.006 and isinstance(rl[8], float):
                rl[8] = round(rl[8] + 0.2, 2)
                truth["planted"].append({"round": 0, "kind": "sheet_disagree", "row": i, "field": "jump"})
            rev.append(rl)
    for wsx in wb.worksheets:
        for col, wdt in zip("ABCDEFGHIJKLMNOP", [34, 10, 24, 24, 12, 8, 8, 8, 12, 12, 12, 12, 8, 9, 9, 10]):
            wsx.column_dimensions[col].width = wdt
        wsx.freeze_panes = "A2"
    wb.save(path)
    truth.setdefault("rows", {})[fname] = row_truth


if __name__ == "__main__":  # pragma: no cover
    import sys
    from ti import config
    t = generate(config.DEMO_DIR, int(sys.argv[1]) if len(sys.argv) > 1 else config.SEED)
    print(f"{t['children']} children, files: {list(t['files'])}")
    print(f"planted: {len(t['planted'])} issues")
