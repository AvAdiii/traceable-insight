"""Review names: mentions A4 could not link with confidence. The coordinator decides."""

import streamlit as st

import source
import ui
from ti import pipeline, queries

SCHOOL_KEY = "school"


def _state_of(c, cid):
    r = c.execute("SELECT state FROM child_states WHERE child_id = ?", (cid,)).fetchone()
    return r[0] if r else None


def _link(mention_id: int, cid: str, name: str, surface: str) -> None:
    c = ui.conn()
    before = _state_of(c, cid)
    queries.resolve_mention(c, mention_id, cid)
    pipeline.recompute_states(c, st.session_state.get(SCHOOL_KEY, "school_a"))
    after = _state_of(c, cid)
    msg = f"Linked “{surface}” to {name}."
    if before != after:
        msg += f" {name} is now {after}."
    st.toast(msg, icon=":material/link:")


def _undo(mention_id: int, surface: str) -> None:
    c = ui.conn()
    queries.undo_resolution(c, mention_id)
    pipeline.recompute_states(c, st.session_state.get(SCHOOL_KEY, "school_a"))
    st.toast(f"“{surface}” is back in the queue.", icon=":material/undo:")


def item(it: dict) -> None:
    m = it["meta"]
    where = [ui.SOURCE_NAMES[it_kind(it)], ui.day(m.get("date")),
             ui.ref_label(it["source_file"], it["ref"])]
    if m.get("sender"):
        where.insert(1, m["sender"])
    with st.container(border=True, key=f"rv-{it['mention_id']}"):
        st.html(f"""<div class="msg">{ui.highlight(it['text'], it['surface'])}</div>
            <div class="note">{ui.esc(' · '.join(w for w in where if w))}</div>""")
        options = [c["child_id"] for c in it["candidates"]]
        label = {c["child_id"]: f"{c['first']} {c['surname']} · Class {c['class']}"
                 for c in it["candidates"]}
        choice = st.radio(f"Who is “{it['surface']}”?", options, index=None,
                          format_func=label.get, horizontal=True,
                          key=f"pick-{it['mention_id']}")
        a, b, _ = st.columns([1.3, 1.2, 3], gap="small")
        a.button("Link to child", type="primary", disabled=choice is None,
                 key=f"link-{it['mention_id']}", on_click=_link,
                 args=(it["mention_id"], choice, label.get(choice, "").split(" · ")[0],
                       it["surface"]), use_container_width=True)
        if b.button("View source", key=f"vs-{it['mention_id']}", type="tertiary",
                    icon=":material/open_in_new:"):
            source.show(it["line_id"], it["surface"])


def it_kind(it: dict) -> str:
    f = it["source_file"]
    if f.startswith("attendance"):
        return "attendance"
    return {"whatsapp.txt": "whatsapp", "coach_forms.csv": "coach_form",
            "assessments.csv": "assessment"}.get(f, "guideline")


def page() -> None:
    c = ui.conn()
    if c is None:
        ui.no_run_notice()
        return
    queue = queries.review_queue(c)
    st.html(f"""<h1 class="page-title">Review names</h1>
        <p class="page-sub">These names could belong to more than one child, so they are not
        linked yet. Pick who each one is; states update straight away.</p>""")
    st.html('<div class="section-t">Waiting · ' + str(len(queue)) + "</div>")
    if not queue:
        st.html(f"""<div class="card empty">{ui.icon('ontrack', 'ic big pass')}
            <h3>No names waiting</h3><p>Every name in the sources is linked to one child.</p>
            </div>""")
    for it in queue:
        item(it)

    done = queries.resolved_mentions(c)
    if done:
        st.html(f'<div class="section-t">Decided · {len(done)}</div>')
        for d in done:
            with st.container(border=True, key=f"dn-{d['mention_id']}"):
                a, b = st.columns([5, 1], vertical_alignment="center")
                a.html(f"""<div class="msg">“{ui.esc(d['surface'])}” is
                    <strong>{ui.esc(d['first'])} {ui.esc(d['surname'])}</strong>
                    <span class="muted">· Class {ui.esc(d['class'])}</span></div>
                    <div class="note">{ui.esc(ui.SOURCE_NAMES[it_kind(d)])} ·
                    {ui.esc(ui.ref_label(d['source_file'], d['ref']))}</div>""")
                b.button("Undo", key=f"undo-{d['mention_id']}", on_click=_undo,
                         args=(d["mention_id"], d["surface"]), use_container_width=True)


page()
