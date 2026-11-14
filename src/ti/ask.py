"""Ask: a question becomes one structured query; the answer is computed from cited cells.

The language model (in the browser, or Ollama on the laptop) only fills the QUERY schema below.
It never sees children's data and never writes the answer. When no model is available, parse()
does the same job with rules. run() validates the query, so a bad model output cannot do harm.
"""

import re

from ti import identity, queries, shortlist
from ti.db import Child, Measurement, School
from ti.pipeline import VALID
from ti.template import TESTS
from sqlalchemy import select

ACTIONS = ["children", "child", "compare", "shortlist", "schools", "count"]
FLAGS = list(queries.FLAG_META)
SORTS = ["best", "worst", "improved"]
MAX_LIMIT = 50  # longest list Ask shows; small models sometimes emit runaway numbers
MAX_COMPARE = 4  # children side by side

SCHEMA = {
    "type": "object",
    "properties": {
        "action": {"type": "string", "enum": ACTIONS},
        "name": {"type": ["string", "null"]},
        "names": {"type": ["array", "null"], "items": {"type": "string"}},
        "school": {"type": ["string", "null"]},
        "gender": {"type": ["string", "null"], "enum": ["Boys", "Girls", None]},
        "age_min": {"type": ["integer", "null"]},
        "age_max": {"type": ["integer", "null"]},
        "klass": {"type": ["string", "null"]},
        "test": {"type": ["string", "null"], "enum": list(TESTS) + ["composite", None]},
        "discipline": {"type": ["string", "null"], "enum": list(shortlist.DISCIPLINES) + [None]},
        "flag": {"type": ["string", "null"], "enum": FLAGS + [None]},
        "sort": {"type": ["string", "null"], "enum": SORTS + [None]},
        "limit": {"type": ["integer", "null"]},
    },
    "required": ["action"],
}

EXAMPLES = [
    ("Who are the 5 fastest girls under 12?",
     {"action": "children", "gender": "Girls", "age_max": 11, "test": "shuttle", "sort": "best", "limit": 5}),
    ("Pick 4 boys aged 12 to 14 for the 100 m sprint from Ramnagar",
     {"action": "shortlist", "discipline": "sprint", "gender": "Boys", "age_min": 12, "age_max": 14,
      "limit": 4, "school": "Ramnagar"}),
    ("Which children in Class V need a push?", {"action": "children", "klass": "Class V", "flag": "push", "sort": "worst"}),
    ("What is Rishitha's broad jump?", {"action": "child", "name": "Rishitha", "test": "jump"}),
    ("Faizan vs Imran in broad jump", {"action": "compare", "names": ["Faizan", "Imran"], "test": "jump"}),
    ("Which school throws the best?", {"action": "schools", "test": "ball", "sort": "best"}),
    ("How many children improved since baseline?", {"action": "count", "flag": "improved"}),
    ("Who improved the most in Kondapur?", {"action": "children", "school": "Kondapur", "sort": "improved", "limit": 10}),
]

SUGGESTED = [
    "Top 5 fastest girls under 12",
    "Pick 4 boys aged 12–14 for the 100 m sprint",
    "Who needs a push in Class V?",
    "Which school jumps the farthest?",
    "Who improved the most since baseline?",
    "Best throwers in ZPHS Lingampally",
    "Mohammed Faizan vs Mohammed Imran",
]


def prompt(school_names: list[str]) -> dict:
    tests = "; ".join(f"{k} = {t.full} ({'lower is better' if t.lower_is_better else 'higher is better'})"
                      for k, t in TESTS.items())
    disc = "; ".join(f"{k} = {v['label']} ({v['examples']})" for k, v in shortlist.DISCIPLINES.items())
    system = (
        "You turn a sports programme coordinator's question into ONE JSON query. Reply with JSON only.\n"
        f"actions: children (a filtered, sorted list), child (one named child), compare (two to four "
        f"named children side by side; put every name in names), shortlist (pick "
        f"athletes for a race or field event), schools (compare schools), count.\n"
        f"tests: {tests}; composite = overall.\n"
        "fastest/quickest/speed -> shuttle; jump -> jump; throw/strong/shot put -> ball; "
        "stamina/endurance/distance -> relay.\n"
        f"disciplines for shortlist: {disc}.\n"
        f"flags: top (top performers), improved, push (need a push / attention / struggling), "
        f"declining, missing (missing tests).\n"
        "'under 12' or 'U-12' means age_max 11. Classes are written 'Class I' to 'Class X'.\n"
        f"schools: {', '.join(school_names)}. Use the school's short name if one is mentioned.\n"
        "Use null for anything not asked.")
    return {"system": system, "schema": SCHEMA,
            "examples": [{"q": q, "a": a} for q, a in EXAMPLES], "suggested": SUGGESTED}


# ------------------------------------------------------------------ rules

_WORDNUM = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
            "eight": 8, "nine": 9, "ten": 10, "twelve": 12, "fifteen": 15, "twenty": 20}
_STOP = {"primary", "school", "schools", "upper", "high", "the", "of", "govt", "mrc", "natco",
         "zilla", "parishad", "nagar", "mpups"}


def _school(q: str, schools: list[School]) -> str | None:
    ql = q.lower()
    for x in schools:
        if x.short.lower() in ql:
            return x.id
    for x in schools:
        toks = [t for t in re.findall(r"[a-z]+", (x.name + " " + x.short).lower())
                if t not in _STOP and len(t) > 3]
        if any(re.search(rf"\b{t}\b", ql) for t in toks):
            return x.id
    return None


def parse(question: str, schools: list[School], child_names: list[str] | None = None) -> dict:
    q = question.strip()
    ql = q.lower().replace("–", "-")
    for w, n in _WORDNUM.items():
        ql = re.sub(rf"\b{w}\b", str(n), ql)
    spec: dict = {"action": "children"}
    if re.search(r"\bgirls?\b|\bfemale", ql):
        spec["gender"] = "Girls"
    elif re.search(r"\bboys?\b|\bmale", ql):
        spec["gender"] = "Boys"
    m = re.search(r"\b(?:under|u)[\s-]?(\d{1,2})\b", ql)
    if m:
        spec["age_max"] = int(m.group(1)) - 1
    m = re.search(r"\b(?:aged?|ages)\s*(\d{1,2})\s*(?:-|to|and)\s*(\d{1,2})", ql)
    if m:
        spec["age_min"], spec["age_max"] = int(m.group(1)), int(m.group(2))
    m = re.search(r"\b(?:over|above|older than)\s*(\d{1,2})\b", ql)
    if m:
        spec["age_min"] = int(m.group(1)) + 1
    m = re.search(r"\bclass\s*([ivx]+|\d{1,2})\b", ql)
    if m:
        from ti.template import norm_class
        spec["klass"] = norm_class(m.group(1))
    m = re.search(r"\b(?:top|best|first|pick|choose|select|fastest|strongest)\s*(\d{1,3})\b", ql) \
        or re.search(r"\b(\d{1,3})\s*(?:fastest|best|strongest|top|children|kids|boys|girls|students|athletes)\b", ql)
    if m:
        spec["limit"] = int(m.group(1))
    sch = _school(ql, schools)
    if sch:
        spec["school"] = sch
    if re.search(r"fast|quick|speed|sprint|shuttle|agil", ql):
        spec["test"] = "shuttle"
    elif re.search(r"jump", ql):
        spec["test"] = "jump"
    elif re.search(r"throw|shot ?put|strong|power|ball", ql):
        spec["test"] = "ball"
    elif re.search(r"stamina|endur|distance|relay|600|800|long run", ql):
        spec["test"] = "relay"
    if re.search(r"improv|progress|most gain", ql):
        spec["sort"] = "improved"
        if re.search(r"how many|count", ql):
            spec["flag"] = "improved"
    elif re.search(r"declin|slower|drop|worse|fell", ql):
        spec["flag"] = "declining"
    elif re.search(r"push|attention|struggl|weak|lowest|worst|behind|help", ql):
        spec["flag"] = "push"
        spec["sort"] = "worst"
    elif re.search(r"missing|not tested|absent|no data", ql):
        spec["flag"] = "missing"
    elif re.search(r"top|best|fastest|strongest|star|champion|talent", ql):
        spec["sort"] = "best"
    if re.search(r"\b(pick|choose|select|shortlist|team|squad|for the|for a)\b", ql) and \
            re.search(r"sprint|\d+\s?m\b|relay|jump|throw|shot|race|run|meet|event|athlet", ql):
        spec["action"] = "shortlist"
        if re.search(r"relay|4\s?x", ql):
            spec["discipline"] = "relay"
        elif re.search(r"jump", ql):
            spec["discipline"] = "long_jump"
        elif re.search(r"throw|shot", ql):
            spec["discipline"] = "throw"
        elif re.search(r"\b(400|600|800|1500)\s?m|distance|endur", ql):
            spec["discipline"] = "endurance"
        elif re.search(r"all.?round", ql):
            spec["discipline"] = "all_round"
        else:
            spec["discipline"] = "sprint"
    elif re.search(r"which school|compare schools|schools? (?:is|are|do|does)|by school|each school", ql):
        spec["action"] = "schools"
    elif re.search(r"how many|number of|count", ql):
        spec["action"] = "count"
    names = _versus(q, schools)
    if names:
        return {"action": "compare", "names": names, **({"test": spec["test"]} if "test" in spec else {})}
    name = None
    m = re.search(r"([A-Za-z][A-Za-z. ]{1,40}?)['’]s\b", q)
    if m:
        name = m.group(1).strip()
        name = re.sub(r"^(what is|what's|show|how is|is|was|get)\s+", "", name, flags=re.I).strip()
    if not name:
        m = re.search(r"\b(?:how is|how's|show me|show|profile of|about|find)\s+([A-Z][\w.]+(?:\s+[A-Z][\w.]+)?)", q)
        if m:
            name = m.group(1)
    if name and name.lower() not in {"who", "which", "what", "the"}:
        spec = {"action": "child", "name": name, **({"test": spec["test"]} if "test" in spec else {})}
    return spec


# "A vs B", "A versus B", "compare A, B and C": two to four named children.
_VS = re.compile(r"\s+(?:vs\.?|versus|v/s|v\.)\s+", re.I)
_COMPARE = re.compile(r"^\s*compare\s+(.+)$", re.I)
_TAIL = re.compile(r"\s+(?:in|on|for|at|by)\s+.*$|[?.!]+\s*$", re.I)
_GROUP = re.compile(r"\b(boys?|girls?|schools?|class(?:es)?|children|kids|students|baseline|midline|"
                    r"endline|rounds?|everyone|all)\b", re.I)


def _versus(q: str, schools: list[School]) -> list[str] | None:
    body = _TAIL.sub("", q.strip())
    m = _COMPARE.match(body)
    if m:
        parts = re.split(r"\s*,\s*|\s+(?:and|with|to|vs\.?|versus|v/s)\s+|\s*&\s*", m.group(1), flags=re.I)
    elif _VS.search(body):
        parts = _VS.split(body)
    else:
        return None
    names = [re.sub(r"\s+", " ", _TAIL.sub("", re.sub(r"['’]s\b.*$", "", x))).strip(" ,") for x in parts]
    names = [n for n in names if n]
    if len(names) < 2 or any(_GROUP.search(n) or _school(n.lower(), schools) for n in names):
        return None
    return names[:MAX_COMPARE]


# ------------------------------------------------------------------ run

def clean_spec(spec: dict) -> dict:
    out = {"action": spec.get("action") if spec.get("action") in ACTIONS else "children"}
    for k in ("name", "school", "klass"):
        if isinstance(spec.get(k), str) and spec[k].strip():
            out[k] = spec[k].strip()
    if out["action"] == "compare":
        names, seen = [], set()
        for n in spec.get("names") if isinstance(spec.get("names"), list) else []:
            if isinstance(n, str) and n.strip() and n.strip().lower() not in seen:
                seen.add(n.strip().lower())
                names.append(n.strip())
        if len(names) >= 2:
            out["names"] = names[:MAX_COMPARE]
        elif names:
            out = {"action": "child", "name": names[0]}
        else:
            out = {"action": "children"}
    if spec.get("gender") in ("Boys", "Girls"):
        out["gender"] = spec["gender"]
    for k, hi in (("age_min", 25), ("age_max", 25), ("limit", MAX_LIMIT)):
        try:
            if spec.get(k) is not None:
                out[k] = max(0, min(hi, int(spec[k])))
        except (TypeError, ValueError):
            pass
    if spec.get("test") in list(TESTS) + ["composite"]:
        out["test"] = spec["test"]
    if spec.get("discipline") in shortlist.DISCIPLINES:
        out["discipline"] = spec["discipline"]
    if spec.get("flag") in FLAGS:
        out["flag"] = spec["flag"]
    if spec.get("sort") in SORTS:
        out["sort"] = spec["sort"]
    if out["action"] == "shortlist" and "discipline" not in out:
        out["discipline"] = {"jump": "long_jump", "ball": "throw", "relay": "endurance"}.get(
            out.get("test"), "sprint")
    return out


# Filters the rules read reliably from the wording; a small model sometimes drops them.
_FILLABLE = ("school", "gender", "age_min", "age_max", "klass")


def merge(model: dict, rules: dict) -> dict:
    """Keep the model's reading of the question; fill filters it left out from the rules parse.

    Explicit wording beats the model: a count ("pick 5") sets the limit, "how many" makes it a
    count, and flag words ("struggling", "missing tests") set the flag and its sort order.
    """
    if not model:  # no model reading at all (fallback path): the rules parse is the answer
        return dict(rules)
    out = dict(model)
    if rules.get("action") == "compare":  # "A vs B" wording is unambiguous; small models drop names, add tests
        return rules
    if out.get("action") in ("child", "compare"):
        return out
    if rules.get("action") == "count":
        out["action"] = "count"
    if rules.get("flag") and rules["flag"] != out.get("flag"):
        out["flag"] = rules["flag"]
        out["sort"] = rules.get("sort")
    for k in _FILLABLE:
        if out.get(k) is None and rules.get(k) is not None:
            out[k] = rules[k]
    if rules.get("limit") is not None:
        out["limit"] = rules["limit"]
    return out


def _resolve_school(s, v: str | None, allowed) -> str | None:
    if not v:
        return None
    schools = s.scalars(select(School)).all()
    for x in schools:
        if v in (x.id, x.name) or v.lower() == x.short.lower():
            return x.id
    return _school(v, schools)


def chips(spec: dict, s) -> list[str]:
    out = []
    if spec.get("school"):
        x = s.get(School, spec["school"])
        out.append(x.short if x else spec["school"])
    if spec.get("gender"):
        out.append(spec["gender"])
    a, b = spec.get("age_min"), spec.get("age_max")
    if a is not None and b is not None:
        out.append(f"Age {a}–{b}")
    elif b is not None:
        out.append(f"Under {b + 1}")
    elif a is not None:
        out.append(f"Age {a}+")
    if spec.get("klass"):
        out.append(spec["klass"])
    if spec.get("test") in TESTS:
        out.append(TESTS[spec["test"]].label)
    if spec.get("discipline"):
        out.append(shortlist.DISCIPLINES[spec["discipline"]]["label"])
    if spec.get("flag"):
        out.append(queries.FLAG_META[spec["flag"]]["label"])
    if spec.get("sort") == "improved":
        out.append("Most improved")
    return out


def run(s, raw_spec: dict, allowed) -> dict:
    spec = clean_spec(raw_spec)
    sch = _resolve_school(s, spec.get("school"), allowed)
    if spec.get("school") and not sch:
        spec.pop("school")
    elif sch:
        spec["school"] = sch
    if allowed is not None and sch and sch not in allowed:
        return {"kind": "empty", "title": "Not in your schools", "sentence":
                "That school is not assigned to you.", "spec": spec, "chips": chips(spec, s), "rows": []}
    act = spec["action"]
    test = spec.get("test")
    if act == "child":
        return _child(s, spec, allowed)
    if act == "compare":
        return _compare(s, spec, allowed)
    if act == "shortlist":
        disc = shortlist.DISCIPLINES[spec["discipline"]]
        ranked, held, pool = shortlist.rank(
            s, disc["weights"], gender=spec.get("gender", "Any"), age_min=spec.get("age_min"),
            age_max=spec.get("age_max"), school_ids={sch} if sch else allowed)
        n = spec.get("limit") or 5
        return {"kind": "shortlist", "title": f"Suggested for {disc['label'].lower()}",
                "sentence": f"Best {n} of {pool} eligible children by {', '.join(TESTS[f].label.lower() for f in disc['weights'])} "
                            f"percentiles. Values waiting for a data check are not used.",
                "spec": spec, "chips": chips(spec, s), "rows": ranked[:n], "reserves": ranked[n:n + 2],
                "held": held[:5]}
    if act == "schools":
        rows = queries.schools_summary(s, allowed)
        key = (lambda x: x["skills"].get(test) or 0) if test in TESTS else (lambda x: x["composite"] or 0)
        rows.sort(key=key, reverse=spec.get("sort") != "worst")
        what = TESTS[test].label.lower() if test in TESTS else "overall score"
        return {"kind": "schools", "title": f"Schools by {what}",
                "sentence": f"Median percentile of each school's children on {what} in their latest round.",
                "spec": spec, "chips": chips(spec, s), "rows": rows}
    sort = spec.get("sort") or ("worst" if spec.get("flag") == "push" else "best")
    res = queries.children(s, allowed, school=sch, klass=spec.get("klass"), gender=spec.get("gender"),
                           age_min=spec.get("age_min"), age_max=spec.get("age_max"),
                           flag=spec.get("flag"), test=test if test in TESTS else None, sort=sort,
                           limit=spec.get("limit") or (200 if act == "count" else 20))
    if act == "count":
        by = {}
        for r in queries.children(s, allowed, school=sch, klass=spec.get("klass"), gender=spec.get("gender"),
                                  age_min=spec.get("age_min"), age_max=spec.get("age_max"),
                                  flag=spec.get("flag"), limit=10_000)["rows"]:
            by[r["school"]] = by.get(r["school"], 0) + 1
        return {"kind": "count", "title": f"{res['total']} children", "count": res["total"],
                "sentence": "Counted from each child's latest round.", "spec": spec,
                "chips": chips(spec, s), "by_school": by, "rows": res["rows"][:10]}
    rows = res["rows"]
    if test in TESTS:
        _attach_cites(s, rows, test)
        rows = [r for r in rows if r["tests"].get(test, {}).get("status") in VALID] if sort != "improved" else rows
    what = TESTS[test].label.lower() if test in TESTS else "overall score"
    title = {"best": f"Best by {what}", "worst": f"Lowest by {what}",
             "improved": "Most improved"}.get(sort, "Children")
    if spec.get("flag"):
        title = queries.FLAG_META[spec["flag"]]["label"]
    return {"kind": "children", "title": title, "test": test,
            "sentence": f"{res['total']} children match. Ranked by percentile among children of the same "
                        f"gender and age; every value opens its spreadsheet cell.",
            "spec": spec, "chips": chips(spec, s), "rows": rows}


def _attach_cites(s, rows, test):
    from ti.queries import cite
    ids = [r["id"] for r in rows]
    latest = queries.latest_by_child(s, None)
    for m in s.scalars(select(Measurement).where(Measurement.child_id.in_(ids), Measurement.field == test)):
        if latest.get(m.child_id) and latest[m.child_id].round_id == m.round_id:
            for r in rows:
                if r["id"] == m.child_id:
                    r["cite"] = cite(s, m)


def _find(s, name: str, allowed) -> tuple[Child | None, list[Child]]:
    """One child for a name (or a child id), else the close matches to choose from."""
    k = s.get(Child, name)
    if k is not None and (allowed is None or k.school_id in allowed):
        return k, [k]
    q = select(Child)
    if allowed is not None:
        q = q.where(Child.school_id.in_(allowed))
    scored = sorted(((identity.name_sim(name, k.name), k) for k in s.scalars(q)), key=lambda x: -x[0])
    good = [(sc, k) for sc, k in scored if sc >= 85][:8]
    if len(good) == 1 or (good and good[0][0] - good[1][0] >= 5):
        return good[0][1], [good[0][1]]
    return None, [k for _, k in good]


def _rows_for(s, allowed, kids: list[Child]) -> list[dict]:
    ids = {k.id for k in kids}
    rows = [r for r in queries.children(s, allowed, limit=10_000)["rows"] if r["id"] in ids]
    return sorted(rows, key=lambda r: [k.id for k in kids].index(r["id"]))


def _child(s, spec, allowed) -> dict:
    name = spec.get("name") or ""
    k, matches = _find(s, name, allowed)
    if not matches:
        return {"kind": "empty", "title": "No child found", "spec": spec, "chips": [name],
                "sentence": f"No child's name is close to “{name}”. Try the full name.", "rows": []}
    if k is None:
        return {"kind": "children", "title": f"Children named like “{name}”",
                "sentence": "More than one child matches. Pick one.", "spec": spec,
                "chips": [name], "rows": _rows_for(s, allowed, matches)}
    d = queries.child_detail(s, k.id, allowed)
    test = spec.get("test")
    sentence = f"{k.name}, {d['klass']}, {d['school']['short']}."
    fact = None
    if d["rounds"]:
        last = d["rounds"][-1]
        if test in TESTS and test in last["tests"]:
            t = last["tests"][test]
            fact = {"field": test, **t, "round": last["label"]}
            sentence = (f"{k.name}'s {TESTS[test].label.lower()} in {last['label']} was "
                        f"{t['raw']} {t['unit']}" + (f", P{t['percentile']:.0f} among {t['pool']}."
                                                     if t["percentile"] is not None else
                                                     f" ({t['note'] or t['status']})."))
        elif last["composite"] is not None:
            sentence = f"{k.name} is at P{last['composite']:.0f} overall among children of the same age and gender ({last['label']})."
    return {"kind": "child", "title": k.name, "sentence": sentence, "child": d, "fact": fact,
            "spec": spec, "chips": chips(spec, s) + [k.name], "rows": []}


def _compare(s, spec, allowed) -> dict:
    sides, details = [], []
    for name in spec["names"]:
        k, matches = _find(s, name, allowed)
        d = queries.child_detail(s, k.id, allowed) if k else None
        details.append(d)
        sides.append({"query": name, "matches": _rows_for(s, allowed, matches) if k is None else [],
                      "child": d and {"id": d["id"], "name": d["name"], "gender": d["gender"], "klass": d["klass"],
                                      "school": d["school"]["short"], "age": d["rounds"][-1]["age"] if d["rounds"] else None,
                                      "round": d["rounds"][-1]["label"] if d["rounds"] else None,
                                      "composite": d["rounds"][-1]["composite"] if d["rounds"] else None}})
    title = " vs ".join(x["child"]["name"] if x["child"] else x["query"] for x in sides)
    base = {"kind": "compare", "title": title, "spec": spec, "rows": [], "sides": sides,
            "chips": chips(spec, s) + [x["child"]["name"] if x["child"] else x["query"] for x in sides]}
    if any(d is None for d in details):
        missing = [x["query"] for x in sides if x["child"] is None]
        none = [x["query"] for x in sides if x["child"] is None and not x["matches"]]
        sentence = (f"No child's name is close to “{none[0]}”. Try the full name." if none else
                    f"More than one child is called {' or '.join(f'“{n}”' for n in missing)}. Pick one.")
        return {**base, "table": [], "sentence": sentence}
    table = []
    want = spec.get("test")
    for f, t in TESTS.items():
        cells = []
        for d in details:
            c = d["rounds"][-1]["tests"].get(f) if d["rounds"] else None
            cells.append(c and {k: c[k] for k in ("value", "raw", "unit", "status", "note", "percentile", "cite")})
        pcts = [c["percentile"] if c and c["status"] in VALID else None for c in cells]
        known = [p for p in pcts if p is not None]
        winner = pcts.index(max(known)) if len(known) == len(pcts) and known.count(max(known)) == 1 else None
        table.append({"field": f, "label": t.label, "unit": t.unit, "lower_is_better": t.lower_is_better,
                      "asked": f == want, "cells": cells, "winner": winner})
    if want in TESTS:
        table.sort(key=lambda r: not r["asked"])
    lead = table[0]
    names = [d["name"] for d in details]
    if lead["winner"] is not None:
        w = lead["winner"]
        sentence = (f"{names[w]} leads on {lead['label'].lower()} at P{lead['cells'][w]['percentile']:.0f}. "
                    if want in TESTS else "")
    else:
        sentence = ""
    comps = [x["child"]["composite"] for x in sides]
    if None not in comps:
        best = max(range(len(comps)), key=lambda i: comps[i])
        sentence += f"Overall, {names[best]} is higher at P{comps[best]:.0f}. "
    sentence += ("Percentiles compare each child with children of the same age and gender, so different "
                 "ages are fair to compare. Every value opens its spreadsheet cell.")
    return {**base, "table": table, "sentence": sentence}
