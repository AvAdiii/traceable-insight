"""Design tokens, CSS and small HTML building blocks for the coordinator view.

Colour is never the only carrier of meaning: every state has a glyph and a label too.
All text tokens are >= 4.5:1 on both surfaces in light and dark (see docs/design.md).
"""

import html
import json
from urllib.parse import quote

import streamlit as st

from ti import config
from ti.state import ATTENTION, CONFLICT, GAP, ON_TRACK
from ti.store import db

TOKENS = {
    "light": {
        "bg": "#F5F5F7", "card": "#FFFFFF", "label": "#1D1D1F", "secondary": "#6E6E73",
        "separator": "#E3E3E8", "fill": "#F0F0F3", "accent": "#0066CC",
        "conflict": "#8E3FB0", "gap": "#5E5E66", "attention": "#B83A00", "ontrack": "#1D7A35",
        "mark": "#FFED91", "cited": "#EAF2FC", "shadow": "0 1px 2px rgba(0,0,0,.06)",
    },
    "dark": {
        "bg": "#1C1C1E", "card": "#2C2C2E", "label": "#F5F5F7", "secondary": "#AEAEB2",
        "separator": "#3A3A3C", "fill": "#343437", "accent": "#4DA3FF",
        "conflict": "#D79BFF", "gap": "#B4B4BB", "attention": "#FF9F43", "ontrack": "#4CD964",
        "mark": "#6B5F23", "cited": "#22344A", "shadow": "none",
    },
}

ICONS = {
    "conflict": '<path d="M8 3 4 7l4 4"/><path d="M4 7h16"/><path d="m16 21 4-4-4-4"/><path d="M20 17H4"/>',
    "gap": '<circle cx="12" cy="12" r="10" stroke-dasharray="3.2 3"/><path d="M9.1 9a3 3 0 0 1 5.8 1c0 2-3 3-3 3"/><path d="M12 17h.01"/>',
    "attention": '<path d="m21.7 18-8-14a2 2 0 0 0-3.5 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.7-3"/><path d="M12 9v4"/><path d="M12 17h.01"/>',
    "ontrack": '<circle cx="12" cy="12" r="10"/><path d="m9 12 2 2 4-4"/>',
    "whatsapp": '<path d="M7.9 20A9 9 0 1 0 4 16.1L2 22Z"/>',
    "coach_form": '<rect width="8" height="4" x="8" y="2" rx="1"/><path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/><path d="M9 12h6M9 16h4"/>',
    "attendance": '<rect width="18" height="18" x="3" y="3" rx="2"/><path d="M3 9h18M3 15h18M9 3v18"/>',
    "assessment": '<circle cx="12" cy="14" r="8"/><path d="M10 2h4"/><path d="m12 14 3-3"/>',
    "guideline": '<path d="M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H20v20H6.5a2.5 2.5 0 0 1 0-5H20"/>',
    "check": '<path d="M20 6 9 17l-5-5"/>',
    "cross": '<path d="M18 6 6 18M6 6l12 12"/>',
    "chevron": '<path d="m9 18 6-6-6-6"/>',
}

STATE = {
    CONFLICT: {"key": "conflict", "short": "Conflict",
               "help": "Two records disagree. Check both sources before acting."},
    GAP: {"key": "gap", "short": "Not enough info",
          "help": "Too few records to judge progress yet."},
    ATTENTION: {"key": "attention", "short": "Needs attention",
                "help": "Meets a guideline trigger for extra coaching attention."},
    ON_TRACK: {"key": "ontrack", "short": "On track",
               "help": "No guideline trigger and enough records to judge."},
}

SOURCE_NAMES = {
    "whatsapp": "WhatsApp group", "coach_form": "Coach session form",
    "attendance": "Attendance sheet", "assessment": "Fitness assessment",
    "guideline": "Programme guideline",
}

MONTHS = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()


def esc(s) -> str:
    return html.escape(str(s), quote=True)


def icon(name: str, cls: str = "ic", label: str | None = None) -> str:
    """A glyph drawn with a CSS mask so it inherits the text colour. st.html strips inline
    <svg>, so the SVG lives in the stylesheet as a data URI instead."""
    aria = f'role="img" aria-label="{esc(label)}"' if label else 'aria-hidden="true"'
    return f'<span class="{cls} i-{name}" {aria}></span>'


def _icon_css() -> str:
    rules = []
    for name, paths in ICONS.items():
        svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
               'stroke="black" stroke-width="2" stroke-linecap="round" '
               f'stroke-linejoin="round">{paths}</svg>')
        rules.append(f'.i-{name} {{ --i: url("data:image/svg+xml,{quote(svg)}"); }}')
    return "\n".join(rules)


def day(iso: str | None) -> str:
    if not iso:
        return ""
    y, m, d = iso.split("-")
    return f"{int(d)} {MONTHS[int(m) - 1]}"


def ref_label(source_file: str, ref: str) -> str:
    kind, _, n = ref.partition(":")
    noun = {"msg": "message", "row": "row", "sec": "section"}.get(kind, kind)
    name = source_file.removesuffix(".csv").removesuffix(".txt").removesuffix(".md")
    if name.startswith("attendance_wk"):
        name = f"week {name.removeprefix('attendance_wk')}"
        return f"{name}, {noun} {n}"
    return f"{noun} {n}"


def highlight(text: str, quote: str | None) -> str:
    """Escape text and wrap the first occurrence of quote in <mark>: the receipt."""
    if not quote or quote not in text or quote == text:
        return esc(text).replace("\n", "<br>")
    i = text.index(quote)
    out = esc(text[:i]) + f"<mark>{esc(quote)}</mark>" + esc(text[i + len(quote):])
    return out.replace("\n", "<br>")


def state_badge(state: str, size: str = "") -> str:
    s = STATE[state]
    return (f'<span class="badge {s["key"]} {size}">{icon(s["key"])}'
            f'<span>{esc(state)}</span></span>')


def conn():
    path = config.db_path(st.session_state.get("school", "school_a"))
    if not path.exists():
        return None
    return db.connect(path)


def meta(c) -> dict:
    return {k: json.loads(v) for k, v in c.execute("SELECT key, value FROM run_meta")}


def no_run_notice() -> None:
    st.html(f"""<div class="empty">{icon('guideline', 'ic big')}
      <h3>No pipeline run yet</h3>
      <p>Run the pipeline once, then reload this page.</p>
      <code>uv run python run_pipeline.py --school school_a</code></div>""")


def css(theme: str) -> str:
    t = TOKENS[theme]
    v = "\n".join(f"  --{k}: {val};" for k, val in t.items())
    return f"""<style>
:root {{
{v}
}}
/* ---------- page frame ---------- */
.block-container {{ padding-top: 2.25rem; padding-bottom: 4rem; max-width: 1240px; }}
[data-testid="stSidebarNav"] a span {{ font-size: 15px; }}
h1, h2, h3 {{ letter-spacing: -0.01em; }}
.eyebrow {{ font-size: 13px; color: var(--secondary); margin: 0 0 2px; }}
.page-title {{ font-size: 28px; font-weight: 600; margin: 0; line-height: 1.2;
  color: var(--label); }}
.page-sub {{ font-size: 15px; color: var(--secondary); margin: 6px 0 0; }}
.ic {{ display: inline-block; width: 16px; height: 16px; flex: none; vertical-align: -3px;
  background-color: currentColor; -webkit-mask: var(--i) center / contain no-repeat;
  mask: var(--i) center / contain no-repeat; }}
{_icon_css()}
.ic.big {{ width: 28px; height: 28px; }}
.muted {{ color: var(--secondary); }}

/* ---------- state colour + glyph + label ---------- */
.conflict {{ --tone: var(--conflict); }}
.gap {{ --tone: var(--gap); }}
.attention {{ --tone: var(--attention); }}
.ontrack {{ --tone: var(--ontrack); }}
.badge {{ display: inline-flex; align-items: center; gap: 6px; font-size: 13px;
  font-weight: 600; color: var(--tone); padding: 3px 10px 3px 8px; border-radius: 999px;
  background: color-mix(in srgb, var(--tone) 11%, var(--card));
  border: 1px solid color-mix(in srgb, var(--tone) 28%, transparent); }}
.badge.lg {{ font-size: 15px; padding: 5px 12px 5px 10px; }}

/* ---------- grouped child list ---------- */
.group-h {{ display: flex; align-items: baseline; gap: 8px; margin: 22px 0 6px; }}
.group-h:first-child {{ margin-top: 4px; }}
.group-h .t {{ font-size: 15px; font-weight: 600; color: var(--tone);
  display: inline-flex; gap: 6px; align-items: center; }}
.group-h .n {{ font-size: 13px; color: var(--secondary); }}
.group-help {{ font-size: 13px; color: var(--secondary); margin: 0 0 8px; }}
.row {{ display: flex; align-items: center; gap: 12px; padding: 10px 12px; min-height: 44px;
  background: var(--card); border-radius: 10px; box-shadow: var(--shadow);
  border: 1px solid var(--separator); transition: border-color .12s, background .12s; }}
.row .bar {{ width: 3px; align-self: stretch; border-radius: 3px; background: var(--tone); }}
.row .who {{ flex: 1; min-width: 0; }}
.row .name {{ font-size: 15px; font-weight: 600; color: var(--label); }}
.row .cls {{ font-size: 13px; color: var(--secondary); margin-left: 6px; font-weight: 400; }}
.row .why {{ font-size: 13px; color: var(--secondary); white-space: nowrap; overflow: hidden;
  text-overflow: ellipsis; margin-top: 2px; }}
.row .chev {{ color: var(--secondary); }}
.row[aria-current="true"] {{ border-color: var(--accent);
  background: color-mix(in srgb, var(--accent) 7%, var(--card)); }}
/* the real button sits on top of the row, invisible, so the whole row is the target */
[class*="st-key-row-"] {{ position: relative; gap: 0 !important; }}
[class*="st-key-row-"] .row {{ pointer-events: none; }}
[class*="st-key-row-"] [class*="st-key-btn-"] {{ position: absolute; inset: 0; z-index: 2;
  margin: 0; }}
[class*="st-key-row-"] [class*="st-key-btn-"] button {{ width: 100%; height: 100%;
  opacity: 0; cursor: pointer; }}
[class*="st-key-row-"]:hover .row {{ border-color: color-mix(in srgb, var(--accent) 55%,
  var(--separator)); }}
[class*="st-key-row-"]:has(button:focus-visible) .row {{ outline: 3px solid var(--accent);
  outline-offset: 2px; }}

/* split view: list and detail scroll independently, filling the window */
[data-testid="stLayoutWrapper"]:has(> .st-key-list),
[data-testid="stLayoutWrapper"]:has(> .st-key-detail),
.st-key-list, .st-key-detail {{ height: max(420px, calc(100vh - 160px)) !important; }}
.st-key-list, .st-key-detail {{ padding-right: 8px; }}
.block-container {{ padding-bottom: 1rem !important; }}

/* ---------- cards ---------- */
.card {{ background: var(--card); border: 1px solid var(--separator); border-radius: 12px;
  padding: 16px 18px; box-shadow: var(--shadow); }}
.card + .card {{ margin-top: 12px; }}
.section-t {{ font-size: 13px; font-weight: 600; color: var(--secondary); margin: 14px 0 6px;
  text-transform: none; }}
.hero {{ display: flex; align-items: center; gap: 14px; flex-wrap: wrap; }}
.hero .nm {{ font-size: 28px; font-weight: 600; color: var(--label); line-height: 1.15; }}
.hero .cl {{ font-size: 15px; color: var(--secondary); }}
.reasons {{ margin: 12px 0 0; padding: 0; list-style: none; }}
.reasons li {{ font-size: 15px; color: var(--label); padding-left: 14px; position: relative;
  margin: 6px 0; line-height: 1.45; }}
.reasons li::before {{ content: ""; position: absolute; left: 0; top: .62em; width: 6px;
  height: 6px; border-radius: 50%; background: var(--tone); }}

/* ---------- sidebar ---------- */
.brand {{ padding: 2px 8px 14px; }}
.brand-t {{ font-size: 17px; font-weight: 600; color: var(--label); }}
[data-testid="stSidebarHeader"] {{ height: 2.5rem; min-height: 0; }}
[data-testid="stPageLink"] a {{ min-height: 36px; border-radius: 8px; }}
[data-testid="stPageLink"] a span {{ font-size: 15px; }}

/* ---------- facts: the receipt ---------- */
[class*="st-key-fact-"] {{ padding: 12px 14px !important; background: var(--card);
  box-shadow: var(--shadow); }}
[class*="st-key-fact-"] + [class*="st-key-fact-"] {{ margin-top: -6px; }}
.fact {{ display: grid; grid-template-columns: 20px 1fr; gap: 4px 10px; }}
.fact .src-ic {{ color: var(--secondary); padding-top: 2px; }}
.fact .sum {{ font-size: 15px; color: var(--label); line-height: 1.4; }}
.fact .q {{ font-size: 14px; color: var(--label); line-height: 1.5; margin-top: 4px; }}
.fact .q::before {{ content: "\\201C"; color: var(--secondary); }}
.fact .q::after {{ content: "\\201D"; color: var(--secondary); }}
.fact .m {{ font-size: 13px; color: var(--secondary); margin-top: 4px; }}
mark {{ background: var(--mark); color: var(--label); padding: 1px 3px; border-radius: 3px;
  box-decoration-break: clone; -webkit-box-decoration-break: clone; }}

/* attendance strip: each mark is a button */
.st-key-strip-card {{ background: var(--card); border: 1px solid var(--separator);
  border-radius: 12px; padding: 14px 16px; box-shadow: var(--shadow); }}
.st-key-strip {{ gap: 6px !important; }}
[class*="st-key-cell-"] {{ min-width: 0; align-items: stretch; }}
[class*="st-key-cell-"] button {{ width: 100%; min-height: 32px; height: 32px; padding: 0;
  font-weight: 600; border-radius: 7px; }}
[class*="st-key-cell-P-"] button {{ background: var(--fill); color: var(--label);
  border: 1px solid transparent; }}
[class*="st-key-cell-A-"] button {{ background: color-mix(in srgb, var(--attention) 13%,
  var(--card)); color: var(--attention); border: 1px solid color-mix(in srgb,
  var(--attention) 35%, transparent); }}
[class*="st-key-cell-N-"] button {{ background: transparent; border: 1px dashed
  var(--secondary); color: var(--secondary) !important; opacity: 1; }}
[class*="st-key-cell-"] button p {{ font-weight: 600; }}
[class*="st-key-cell-"] .d {{ font-size: 11px; line-height: 1.25; color: var(--secondary);
  text-align: center; white-space: nowrap; margin-top: 2px; }}
.strip {{ display: grid; grid-template-columns: repeat(12, minmax(0, 1fr)); gap: 6px; }}
.cell {{ text-align: center; }}
.cell .mk {{ height: 30px; border-radius: 7px; display: flex; align-items: center;
  justify-content: center; font-size: 13px; font-weight: 600; }}
.cell .mk.P {{ background: var(--fill); color: var(--label); }}
.cell .mk.A {{ background: color-mix(in srgb, var(--attention) 13%, var(--card));
  color: var(--attention); border: 1px solid color-mix(in srgb, var(--attention) 35%,
  transparent); }}
.cell .mk.N {{ border: 1px dashed var(--secondary); color: var(--secondary); }}
.cell .d {{ font-size: 11px; color: var(--secondary); margin-top: 4px; white-space: nowrap; }}
.legend {{ font-size: 13px; color: var(--secondary); margin-top: 10px; }}

/* fitness table */
table.fit {{ width: 100%; border-collapse: collapse; font-size: 14px; }}
table.fit th {{ text-align: left; font-weight: 600; font-size: 13px; color: var(--secondary);
  padding: 6px 8px; border-bottom: 1px solid var(--separator); }}
table.fit td {{ padding: 8px; border-bottom: 1px solid var(--separator); color: var(--label);
  font-variant-numeric: tabular-nums; }}
table.fit tr:last-child td {{ border-bottom: 0; }}
table.fit .worse {{ color: var(--attention); font-weight: 600; }}

/* ---------- source viewer ---------- */
.src-h {{ display: flex; gap: 8px; align-items: center; font-size: 15px; font-weight: 600;
  color: var(--label); }}
.src-sub {{ font-size: 13px; color: var(--secondary); margin: 2px 0 14px; }}
.lines {{ border: 1px solid var(--separator); border-radius: 10px; overflow: hidden; }}
.ln {{ display: grid; grid-template-columns: 74px 1fr; gap: 12px; padding: 9px 12px;
  border-top: 1px solid var(--separator); font-size: 14px; line-height: 1.5;
  color: var(--label); }}
.ln:first-child {{ border-top: 0; }}
.ln .r {{ font-size: 12px; color: var(--secondary); font-variant-numeric: tabular-nums;
  padding-top: 2px; }}
.ln.hdr {{ background: var(--fill); font-weight: 600; font-size: 13px; }}
.ln.cited {{ background: var(--cited); box-shadow: inset 3px 0 0 var(--accent); }}
.ln .who {{ font-size: 12px; color: var(--secondary); display: block; }}
.mono {{ font-family: ui-monospace, 'SF Mono', 'JetBrains Mono', Menlo, Consolas, monospace;
  font-size: 13px; }}
.note {{ font-size: 13px; color: var(--secondary); margin-top: 12px; }}

/* ---------- review + check ---------- */
.msg {{ font-size: 16px; line-height: 1.5; color: var(--label); }}
.check-row {{ display: grid; grid-template-columns: 28px 1fr auto; gap: 12px;
  align-items: center; padding: 14px 4px; border-top: 1px solid var(--separator); }}
.check-row:first-child {{ border-top: 0; }}
.check-row .lbl {{ font-size: 15px; color: var(--label); font-weight: 600; }}
.check-row .tgt {{ font-size: 13px; color: var(--secondary); }}
.check-row .val {{ font-size: 20px; font-weight: 600; font-variant-numeric: tabular-nums;
  color: var(--label); text-align: right; }}
.pass {{ color: var(--ontrack); }}
.fail {{ color: var(--attention); }}
.verdict {{ display: inline-flex; gap: 6px; align-items: center; font-weight: 600;
  font-size: 13px; }}
.empty {{ text-align: center; padding: 48px 16px; color: var(--secondary); }}
.empty h3 {{ color: var(--label); font-size: 20px; margin: 10px 0 4px; }}
.empty code {{ display: inline-block; margin-top: 10px; }}
.kv {{ margin: 0; padding: 0; display: grid; grid-template-columns: max-content 1fr; gap: 6px 16px; font-size: 14px; }}
.kv dt {{ color: var(--secondary); }}
.kv dd {{ margin: 0; color: var(--label); font-variant-numeric: tabular-nums; }}

/* buttons: comfortable targets, visible focus */
.stButton button, .stDownloadButton button {{ min-height: 36px; }}
button:focus-visible {{ outline: 3px solid var(--accent) !important; outline-offset: 2px; }}
@media (prefers-reduced-motion: reduce) {{ * {{ transition: none !important; }} }}
/* compact width: stack the split view, selected child first, page scrolls */
@media (max-width: 1180px) {{
  [data-testid="stHorizontalBlock"]:has(.st-key-list) {{ flex-direction: column; }}
  [data-testid="stHorizontalBlock"]:has(.st-key-list) > [data-testid="stColumn"] {{
    width: 100% !important; flex: 1 1 auto !important; }}
  [data-testid="stHorizontalBlock"]:has(.st-key-list) > [data-testid="stColumn"]:has(.st-key-detail) {{
    order: -1; }}
  [data-testid="stLayoutWrapper"]:has(> .st-key-list),
  [data-testid="stLayoutWrapper"]:has(> .st-key-detail),
  .st-key-list, .st-key-detail {{ height: auto !important; overflow: visible !important; }}
  [class*="st-key-fact-"] {{ flex-wrap: wrap !important; }}
}}
</style>"""


def inject_css() -> None:
    theme = getattr(st.context.theme, "type", None) or "light"
    st.html(css("dark" if theme == "dark" else "light"))
