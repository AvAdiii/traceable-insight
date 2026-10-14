"""The receipt: a cited line shown in place, with neighbours and the quote highlighted."""

import streamlit as st

import ui
from ti import queries

NOTES = {
    "whatsapp": "Phone numbers, links and media were removed when this chat was imported.",
    "coach_form": "Free-text answer from the coach's session form.",
    "attendance": "Weekly sheet kept by the PE teacher. P = present, A = absent, blank = not "
                  "recorded.",
    "assessment": "Fitness tests entered by the PE teacher.",
    "guideline": "Synthetic guideline: placeholder thresholds, to be validated with HRS.",
}


def _line_html(kind: str, line: dict, quote: str | None) -> str:
    cls = "ln cited" if line["cited"] else "ln"
    ref = ui.esc(ui.ref_label("", line["ref"]).split(", ")[-1])
    m = line["meta"]
    q = quote if line["cited"] else None
    if kind == "whatsapp":
        who = f'{ui.day(m["date"])}, {m["time"]} · {m.get("sender") or ""}'
        body = f'<span class="who">{ui.esc(who)}</span>{ui.highlight(line["text"], q)}'
    elif kind == "coach_form":
        who = f'Session {ui.day(m["date"])} · submitted {m["submitted"]}'
        body = f'<span class="who">{ui.esc(who)}</span>{ui.highlight(line["text"], q)}'
    elif kind == "guideline":
        body = f'<strong>{ui.esc(m["title"])}</strong><br>{ui.highlight(line["text"], q)}'
    else:
        body = f'<span class="mono">{ui.highlight(line["text"], q)}</span>'
    current = ' aria-current="true"' if line["cited"] else ""
    return f'<div class="{cls}"{current}><span class="r">{ref}</span><div>{body}</div></div>'


def render(line_id: int, quote: str | None = None) -> None:
    c = ui.conn()
    ctx = queries.source_context(c, line_id, radius=2)
    kind = ctx["kind"]
    name = ui.SOURCE_NAMES[kind]
    rows = []
    if ctx.get("header"):
        rows.append(f'<div class="ln hdr"><span class="r">header</span>'
                     f'<span class="mono">{ui.esc(ctx["header"])}</span></div>')
    rows += [_line_html(kind, l, quote) for l in ctx["lines"]]
    st.html(f"""
      <div class="src-h">{ui.icon(kind)}<span>{ui.esc(name)}</span></div>
      <div class="src-sub">{ui.esc(ctx["source_file"])} · {ui.esc(ui.ref_label(
          ctx["source_file"], ctx["ref"]))} · highlighted line is the one cited</div>
      <div class="lines" role="list">{''.join(rows)}</div>
      <p class="note">{ui.esc(NOTES[kind])}</p>""")


@st.dialog("Source", width="large")
def show(line_id: int, quote: str | None = None) -> None:
    render(line_id, quote)
