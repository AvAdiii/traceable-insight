"""School view: every child in exactly one of four states, and why, with cited evidence."""

import streamlit as st

import source
import ui
from ti import queries
from ti.generator.roster import SCHOOL
from ti.state import STATES

st.session_state.setdefault("child", st.query_params.get("child"))


def display_names(c) -> dict[str, str]:
    """First name only, unless two children share it: then add the surname initial."""
    rows = c.execute("SELECT child_id, first, surname FROM children").fetchall()
    firsts = [r["first"] for r in rows]
    return {r["child_id"]: r["first"] if firsts.count(r["first"]) == 1
            else f"{r['first']} {r['surname'][0]}." for r in rows}


def _select(cid: str) -> None:
    st.session_state.child = cid
    st.query_params["child"] = cid


def child_list(groups: dict, names: dict) -> None:
    selected = st.session_state.child
    for state in STATES:
        kids = groups[state]
        s = ui.STATE[state]
        st.html(f"""<div class="group-h {s['key']}"><span class="t">{ui.icon(s['key'])}
            {ui.esc(state)}</span><span class="n">{len(kids)}</span></div>
            <p class="group-help">{ui.esc(s['help'])}</p>""")
        if not kids:
            st.html('<p class="group-help">Nobody in this group.</p>')
        for k in kids:
            cur = "true" if k["child_id"] == selected else "false"
            with st.container(key=f"row-{k['child_id']}"):
                st.html(f"""<div class="row {s['key']}" aria-current="{cur}">
                    <span class="bar"></span>
                    <div class="who"><div class="name">{ui.esc(names[k['child_id']])}<span class="cls">
                    Class {ui.esc(k['class'])}</span></div>
                    <div class="why">{ui.esc(k['reasons'][0])}</div></div>
                    <span class="chev">{ui.icon('chevron')}</span></div>""")
                st.button(f"{names[k['child_id']]}, Class {k['class']}, {state}: "
                          f"{k['reasons'][0]}",
                          key=f"btn-{k['child_id']}", on_click=_select, args=(k["child_id"],))


def _fact_html(f: dict, show_quote: bool = True) -> str:
    meta = [ui.SOURCE_NAMES[f["kind"]], ui.day(f["date"]),
            ui.ref_label(f["source_file"], f["ref"])]
    if f["surface"] and f["kind"] in ("whatsapp", "coach_form"):
        meta.append(f'written as “{f["surface"]}”')
    quote = (f'<div class="q">{ui.esc(f["quote"])}</div>'
             if show_quote and f["quote"] else "")
    return (f'<div class="fact"><span class="src-ic">{ui.icon(f["kind"])}</span><div>'
            f'<div class="sum">{ui.esc(f["summary"])}</div>{quote}'
            f'<div class="m">{ui.esc(" · ".join(m for m in meta if m))}</div></div></div>')


def fact_card(f: dict, key: str) -> None:
    with st.container(border=True, key=f"fact-{key}", horizontal=True, wrap=False,
                      vertical_alignment="center", gap="small"):
        st.html(_fact_html(f, show_quote=f["kind"] in ("whatsapp", "coach_form")))
        if st.button("View source", key=f"src-{key}", type="tertiary",
                     icon=":material/open_in_new:", width="content",
                     help=f"Open {ui.SOURCE_NAMES[f['kind']].lower()}, "
                          f"{ui.ref_label(f['source_file'], f['ref'])}"):
            source.show(f["line_id"], f["quote"])


def attendance_strip(facts: list[dict]) -> None:
    """Twelve planned sessions. Each recorded mark is a button that opens its sheet row."""
    from ti.generator.profiles import sessions  # the planned programme calendar
    marks = {f["date"]: f for f in facts if f["type"] == "attendance"}
    present = sum(1 for f in marks.values() if f["summary"].startswith("Present"))
    with st.container(key="strip-card"):
        cols = st.columns(12, gap="small")
        for col, d in zip(cols, sessions()):
            iso = d.isoformat()
            f = marks.get(iso)
            val = "N" if f is None else ("P" if f["summary"].startswith("Present") else "A")
            word = {"P": "present", "A": "absent", "N": "not recorded"}[val]
            with col.container(key=f"cell-{val}-{iso}", gap=None):
                if st.button({"P": "P", "A": "A", "N": "–"}[val], key=f"mk-{iso}",
                             disabled=f is None, use_container_width=True,
                             help=f"{ui.day(iso)}: {word}" + ("" if f is None else
                                                             ". Select to view the sheet row.")):
                    source.show(f["line_id"], f["quote"])
                dd, mon = ui.day(iso).split()
                st.html(f'<div class="d">{dd}<br>{mon}</div>')
        missing = 12 - len(marks)
        st.html(f"""<div class="legend">Present at {present} of {len(marks)} recorded sessions{
            f" · {missing} not recorded" if missing else ""}. P present, A absent,
            – not recorded. Select a mark to see its sheet.</div>""")


TESTS = [("50m sprint", "sprint_50m_s", "s", True),
         ("Standing broad jump", "broad_jump_cm", "cm", False),
         ("600m run", "run_600m_s", "s", True)]


def fitness_table(facts: list[dict]) -> None:
    rounds = {f["value"]["round"]: f for f in facts if f["type"] == "assessment"}
    if not rounds:
        st.html('<div class="card muted">No fitness assessments on record.</div>')
        return

    def cell(rnd, key, unit):
        f = rounds.get(rnd)
        if f is None or f["value"].get("missing"):
            return None, "not tested" if f is not None else "–"
        v = f["value"][key]
        return v, f"{v:g}{unit}"

    rows = []
    for label, key, unit, lower_better in TESTS:
        b, bt = cell("baseline", key, unit)
        m, mt = cell("midline", key, unit)
        change, cls = "–", ""
        if b is not None and m is not None:
            pct = 100 * (m - b) / b
            worse = pct > 0 if lower_better else pct < 0
            word = ("slower" if lower_better else "shorter") if worse else \
                ("faster" if lower_better else "longer")
            change = f"{abs(pct):.0f}% {word}" if abs(pct) >= 0.5 else "no change"
            # Only sprint and 600m feed the fitness rule, so only they get the warning tone.
            cls = "worse" if worse and lower_better and abs(pct) > 8 else ""
        rows.append(f"<tr><td>{label}</td><td>{ui.esc(bt)}</td><td>{ui.esc(mt)}</td>"
                    f'<td class="{cls}">{ui.esc(change)}</td></tr>')
    st.html(f"""<div class="card"><table class="fit"><thead><tr><th>Test</th><th>Baseline</th>
        <th>Midline</th><th>Change</th></tr></thead><tbody>{''.join(rows)}</tbody></table>
        </div>""")


def detail(cid: str, names: dict) -> None:
    c = ui.conn()
    d = queries.child_detail(c, cid)
    if d is None:
        st.html('<div class="empty"><h3>Child not found</h3></div>')
        return
    s = ui.STATE[d["state"]]
    reasons = "".join(f"<li>{ui.esc(r)}</li>" for r in d["reasons"])
    st.html(f"""<div class="card {s['key']}">
        <div class="hero"><span class="nm">{ui.esc(names[cid])}</span>
        <span class="cl">Class {ui.esc(d['class'])}</span>{ui.state_badge(d['state'], 'lg')}</div>
        <ul class="reasons">{reasons}</ul></div>""")
    if d["rules"]:
        with st.container(horizontal=True, gap="medium", key="rules"):
            for r in d["rules"]:
                label = f"Guideline § {r['ref'].split(':')[1]} · {r['title']}"
                if st.button(label, key=f"rule-{cid}-{r['line_id']}", type="tertiary",
                             icon=":material/menu_book:", width="content",
                             help="Open the guideline section this rule comes from"):
                    source.show(r["line_id"])

    conflict = d["state"] == "Conflict to review"
    evidence = [f for f in d["evidence"] if conflict or f["type"] != "attendance"]
    if evidence:
        title = "Records that disagree" if conflict else "Evidence"
        st.html(f'<div class="section-t">{title}</div>')
        for f in evidence:
            fact_card(f, f"ev-{f['fact_id']}")

    st.html('<div class="section-t">Attendance</div>')
    attendance_strip(d["facts"])
    st.html('<div class="section-t">Fitness</div>')
    fitness_table(d["facts"])

    notes = [f for f in d["facts"] if f["kind"] in ("whatsapp", "coach_form")]
    st.html(f'<div class="section-t">Notes from coach and teacher · {len(notes)}</div>')
    if not notes:
        st.html('<div class="card muted">No notes mention this child yet.</div>')
    for f in notes:
        fact_card(f, f"n-{f['fact_id']}")


def page() -> None:
    c = ui.conn()
    if c is None:
        ui.no_run_notice()
        return
    ov = queries.school_overview(c)
    groups = ov["groups"]
    total = sum(len(v) for v in groups.values())
    m = ov["meta"]
    run = m.get("ran_at", "").replace("T", " at ")
    st.html(f"""<p class="eyebrow">{ui.esc(SCHOOL)}</p><h1 class="page-title">Children</h1>
        <p class="page-sub">{total} children · 6 weeks · 12 sessions · last run {ui.esc(run)}
        </p>""")
    if not st.session_state.child or not any(
            k["child_id"] == st.session_state.child for g in groups.values() for k in g):
        first = next(g[0] for s, g in groups.items() if g)
        st.session_state.child = first["child_id"]
    names = display_names(c)
    left, right = st.columns([5, 7], gap="large")
    with left:
        with st.container(key="list", height=720, border=False):
            child_list(groups, names)
    with right:
        with st.container(key="detail", height=720, border=False):
            detail(st.session_state.child, names)


page()
