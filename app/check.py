"""Ground-truth check: how this run compares with the planted answers."""

import streamlit as st

import ui
from ti import score

ROWS = [
    ("link_accuracy", "Name mentions linked to the right child",
     lambda r: f"{r['link_accuracy']:.1%}", lambda r: f"of {r['mentions_total']} mentions · "
     "target 85% or more"),
    ("conflicts_recovered", "Planted conflicts found",
     lambda r: f"{r['conflicts_recovered']} of {r['conflicts_planted']}",
     lambda r: "target 3 or more"),
    ("gaps_recovered", "Planted gaps found",
     lambda r: f"{r['gaps_recovered']} of {r['gaps_planted']}", lambda r: "target 3 or more"),
    ("citations_resolve", "Cited facts that open their source line",
     lambda r: f"{r['citations_resolve']:.0%}", lambda r: f"of {r['facts_total']} facts · "
     "target 100%"),
]


def page() -> None:
    c = ui.conn()
    if c is None:
        ui.no_run_notice()
        return
    school = st.session_state.get("school", "school_a")
    r = score.compute(school)
    met = r["all_targets_met"]
    verdict = (f'<span class="verdict pass">{ui.icon("check")} All targets met</span>' if met
               else f'<span class="verdict fail">{ui.icon("cross")} Some targets missed</span>')
    st.html(f"""<h1 class="page-title">Ground-truth check</h1>
        <p class="page-sub">Compares this run with the answers planted by the data generator.
        The pipeline never reads the answer file; only this check does.</p>
        <div style="margin-top:12px">{verdict}</div>""")
    rows = []
    for key, label, val, tgt in ROWS:
        ok = r["targets"][key]
        mark = ui.icon("check" if ok else "cross", f"ic {'pass' if ok else 'fail'}",
                       "Pass" if ok else "Fail")
        rows.append(f"""<div class="check-row"><span>{mark}</span><div>
            <div class="lbl">{ui.esc(label)}</div><div class="tgt">{ui.esc(tgt(r))}</div></div>
            <div class="val">{ui.esc(val(r))}</div></div>""")
    st.html(f'<div class="card">{"".join(rows)}</div>')

    st.html(f'<div class="section-t">Child states · {r["states_correct"]} of {r["children"]} '
            f'match the planted state</div>')
    if r["wrong_states"]:
        for w in r["wrong_states"]:
            st.html(f'<div class="card">{ui.esc(w["child_id"])}: expected '
                    f'{ui.state_badge(w["expected"])} got {ui.state_badge(w["got"])}</div>')
    else:
        st.html('<div class="card muted">Every child landed in the planted state.</div>')

    with st.expander(f"Name mentions not linked as planted · {len(r['link_misses'])}"):
        if not r["link_misses"]:
            st.write("None.")
        for m in r["link_misses"]:
            got = {"missing": "not extracted", "review": "sent to review",
                   "unlinked": "not linked"}.get(m["got_status"], m["got_status"])
            if m["got_status"] == "linked":
                got = f"linked to {m['got_child']}"
            st.html(f'<div class="note" style="margin:4px 0">“{ui.esc(m["surface"])}” · '
                    f'{ui.esc(m["file"])} {ui.esc(m["ref"])} · expected {ui.esc(m["child_id"])}'
                    f' · {ui.esc(got)}</div>')

    m = ui.meta(c)
    st.html(f"""<div class="section-t">This run</div><div class="card"><dl class="kv">
        <dt>Model</dt><dd>{ui.esc(m.get('model'))} (local, via Ollama)</dd>
        <dt>Source lines</dt><dd>{m.get('source_lines')}</dd>
        <dt>Facts stored</dt><dd>{m.get('facts')}</dd>
        <dt>Facts rejected</dt><dd>{m.get('rejected_facts')} (quote not found in the source)</dd>
        <dt>Ran at</dt><dd>{ui.esc(str(m.get('ran_at', '')).replace('T', ' '))}
        · {m.get('seconds')} s</dd></dl></div>""")
    st.button("Run check again", icon=":material/refresh:")


page()
