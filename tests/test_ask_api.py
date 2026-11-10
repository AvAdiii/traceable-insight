from fastapi.testclient import TestClient
from sqlalchemy import select

from ti import ask, shortlist
from ti.db import EventItem, School


def test_rule_parser_routes_common_questions(s):
    schools = s.scalars(select(School)).all()
    p = lambda q: ask.clean_spec(ask.parse(q, schools))  # noqa: E731
    assert p("Top 5 fastest girls under 12") == {"action": "children", "gender": "Girls", "age_max": 11,
                                                 "limit": 5, "test": "shuttle", "sort": "best"}
    assert p("Pick 4 boys aged 12-14 for the 100 m sprint")["action"] == "shortlist"
    assert p("Which school jumps the farthest?")["action"] == "schools"
    assert p("Who needs a push in Class V?")["flag"] == "push"
    assert p("What is Rishitha's broad jump?") == {"action": "child", "name": "Rishitha", "test": "jump"}
    assert p("Best throwers in ZPHS Lingampally")["school"].startswith("zilla")


def test_bad_model_output_is_cleaned():
    assert ask.clean_spec({"action": "drop table", "limit": "lots", "test": "iq"}) == {"action": "children"}


def test_runaway_limit_is_capped():
    assert ask.clean_spec({"action": "shortlist", "limit": 5000000000000000})["limit"] == ask.MAX_LIMIT


def test_rules_fill_filters_the_model_dropped(s):
    # Seen with qwen2.5:3b: right action and discipline, but filters dropped and a runaway limit.
    schools = s.scalars(select(School)).all()
    q = "pick 5 boys under 14 for the 800 m race from Moosapet"
    got = ask.merge({"action": "shortlist", "discipline": "endurance", "limit": 5000000000000000},
                    ask.parse(q, schools))
    assert got["action"] == "shortlist" and got["discipline"] == "endurance"
    assert (got["gender"], got["age_max"], got["limit"]) == ("Boys", 13, 5)
    assert "moosapet" in got["school"]


def test_explicit_keywords_beat_model_misreads(s):
    schools = s.scalars(select(School)).all()
    got = ask.merge({"action": "children", "klass": "Class VI", "flag": "top"},
                    ask.parse("who is struggling in class 6", schools))
    assert got["flag"] == "push"
    got = ask.merge({"action": "children", "school": "Kondapur", "flag": "missing"},
                    ask.parse("how many kids in Kondapur are missing tests", schools))
    assert got["action"] == "count"


def test_model_choices_win_over_rules(s):
    schools = s.scalars(select(School)).all()
    model = {"action": "children", "gender": "Girls", "test": "ball", "sort": "best", "klass": "Class VIII"}
    got = ask.merge(model, ask.parse("Which girls in Class VIII throw the farthest?", schools))
    assert {k: got[k] for k in model} == model
    # A named-child answer never picks up list filters.
    assert ask.merge({"action": "child", "name": "Rishitha"}, {"action": "children", "gender": "Girls"}) == \
        {"action": "child", "name": "Rishitha"}


def test_shortlist_cites_every_reason(s):
    item = s.scalar(select(EventItem).where(EventItem.discipline == "sprint"))
    out = shortlist.suggest(s, item)
    assert len(out["selected"]) == item.slots
    for c in out["selected"]:
        assert c["reasons"] and all(r["cite"]["cell"] for r in c["reasons"])


def _client():
    from ti.api import app
    return TestClient(app)


def _tok(c, who):
    return {"Authorization": "Bearer " + c.post("/api/auth/login", json={"email": f"{who}@champion.demo", "password": "champion"}).json()["token"]}


def test_roles_scope_schools_and_actions(workspace):
    c = _client()
    assert c.get("/api/overview").status_code == 401
    m, sv, tr = _tok(c, "manager"), _tok(c, "supervisor"), _tok(c, "trainer")
    assert len(c.get("/api/meta", headers=m).json()["schools"]) == 8
    assert len(c.get("/api/meta", headers=sv).json()["schools"]) == 4
    assert c.post("/api/events", json={"title": "x", "start_date": "2026-12-01"}, headers=tr).status_code == 403
    assert c.put("/api/settings", json={"weights": {"jump": 2}}, headers=sv).status_code == 403


def test_every_child_value_opens_its_cell(workspace):
    c = _client()
    h = _tok(c, "manager")
    cid = c.get("/api/children?limit=1", headers=h).json()["rows"][0]["id"]
    d = c.get(f"/api/children/{cid}", headers=h).json()
    t = next(iter(d["rounds"][0]["tests"].values()))
    r = c.get(f"/api/receipt/{t['cite']['record_id']}?col={t['cite']['cell'].rstrip('0123456789')}", headers=h).json()
    cited = next(x for x in r["rows"] if x["cited"])
    assert r["col"] and cited["row"] == t["cite"]["row"]


# ------------------------------------------------------------------ compare


def test_rules_read_a_versus_question(s):
    schools = s.scalars(select(School)).all()
    p = lambda q: ask.clean_spec(ask.parse(q, schools))  # noqa: E731
    assert p("Faizan vs Imran") == {"action": "compare", "names": ["Faizan", "Imran"]}
    assert p("faizan v/s imran?") == {"action": "compare", "names": ["faizan", "imran"]}
    assert p("Compare Mohammed Faizan and Mohammed Imran in broad jump") == \
        {"action": "compare", "names": ["Mohammed Faizan", "Mohammed Imran"], "test": "jump"}
    assert p("compare Rishitha, Faizan and Imran") == \
        {"action": "compare", "names": ["Rishitha", "Faizan", "Imran"]}
    assert p("Faizan vs Imran's shuttle run") == {"action": "compare", "names": ["Faizan", "Imran"], "test": "shuttle"}
    # Groups are not children.
    assert p("boys vs girls")["action"] != "compare"
    assert p("compare schools")["action"] == "schools"


def test_compare_spec_is_cleaned():
    assert ask.clean_spec({"action": "compare", "names": ["Faizan"]}) == {"action": "child", "name": "Faizan"}
    assert ask.clean_spec({"action": "compare", "names": "Faizan"}) == {"action": "children"}
    got = ask.clean_spec({"action": "compare", "names": [" A ", "a", "B", None, "C", "D", "E"]})
    assert got == {"action": "compare", "names": ["A", "B", "C", "D"]}


def test_versus_wording_beats_a_model_that_kept_one_name(s):
    schools = s.scalars(select(School)).all()
    got = ask.merge({"action": "child", "name": "Faizan", "test": "jump"},
                    ask.parse("Faizan vs Imran in jump", schools))
    assert got["action"] == "compare" and got["names"] == ["Faizan", "Imran"] and got["test"] == "jump"
    # Seen with qwen2.5:3b: a test the question never named.
    got = ask.merge({"action": "compare", "names": ["Faizan", "Imran"], "test": "ball"},
                    ask.parse("Faizan vs Imran", schools))
    assert "test" not in got


def _ids(s, *names):
    from ti.db import Child
    return [s.scalar(select(Child.id).where(Child.name == n)) for n in names]


def test_compare_lines_up_cited_tests_side_by_side(s):
    a, b = _ids(s, "Mohammed Faizan", "Mohammed Imran")
    out = ask.run(s, {"action": "compare", "names": [a, b]}, None)
    assert out["kind"] == "compare"
    assert [x["child"]["id"] for x in out["sides"]] == [a, b]
    assert {r["field"] for r in out["table"]} >= {"jump", "shuttle", "ball", "relay"}
    for r in out["table"]:
        assert len(r["cells"]) == 2
        for c in r["cells"]:
            if c and c["value"] is not None:
                assert c["cite"]["cell"]
        pcts = [c["percentile"] if c else None for c in r["cells"]]
        if None not in pcts and pcts[0] != pcts[1]:
            assert r["winner"] == pcts.index(max(pcts))
    assert out["sentence"]


def test_compare_asks_which_child_when_a_name_is_shared(s):
    (b,) = _ids(s, "Mohammed Imran")
    out = ask.run(s, {"action": "compare", "names": ["Faizan", b]}, None)
    assert out["kind"] == "compare"
    first, second = out["sides"]
    assert first["child"] is None and len(first["matches"]) > 1
    assert all("faizan" in m["name"].lower() for m in first["matches"])
    assert second["child"]["id"] == b
    assert out["table"] == []


def test_compare_api_runs_through_rules(workspace):
    c = _client()
    h = _tok(c, "manager")
    spec = c.post("/api/ask/parse", json={"question": "Faizan vs Imran"}, headers=h).json()
    assert spec["action"] == "compare"
    out = c.post("/api/ask/run", json={"spec": spec, "question": "Faizan vs Imran"}, headers=h).json()
    assert out["kind"] == "compare" and len(out["sides"]) == 2
