"""Source files: the raw synthetic inputs exactly as the pipeline receives them (demo step 1)."""

import pandas as pd
import streamlit as st

import ui
from ti import config

FILES = {
    "WhatsApp chat": ("whatsapp", ["whatsapp.txt"]),
    "Attendance sheets": ("attendance", [f"attendance_wk{i}.csv" for i in range(1, 7)]),
    "Coach session forms": ("coach_form", ["coach_forms.csv"]),
    "Fitness assessments": ("assessment", ["assessments.csv"]),
    "Roster": ("attendance", ["roster.csv", "staff.csv"]),
    "Programme guideline": ("guideline", ["../programme/guideline.md",
                                          "../programme/thresholds.yaml"]),
}


def page() -> None:
    school = st.session_state.get("school", "school_a")
    folder = config.DATA_DIR / school
    st.html(f"""<h1 class="page-title">Source files</h1>
        <p class="page-sub">School A exactly as the pipeline receives it: messy, unedited, and
        synthetic. Phone numbers come from a fake range. The answer file used by the
        ground-truth check is not shown here; the pipeline never reads it.</p>""")
    if not folder.exists():
        ui.no_run_notice()
        return
    choice = st.segmented_control("Source", list(FILES), default="WhatsApp chat",
                                  required=True, label_visibility="collapsed", key="src-pick")
    kind, files = FILES[choice]
    name = files[0]
    if len(files) > 1:
        name = st.selectbox("File", files, format_func=lambda f: f.split("/")[-1],
                            key=f"file-{choice}")
    path = (folder / name).resolve()
    text = path.read_text()
    n_lines = text.count("\n")
    shown = path.relative_to(config.ROOT) if path.is_relative_to(config.ROOT) else path
    st.html(f"""<div class="src-h" style="margin-top:6px">{ui.icon(kind)}
        <span>{ui.esc(path.name)}</span></div>
        <div class="src-sub">{ui.esc(str(shown))} · {n_lines} lines ·
        {path.stat().st_size / 1024:.1f} KB</div>""")
    if path.suffix == ".csv":
        df = pd.read_csv(path, dtype=str, keep_default_na=False)
        st.dataframe(df, hide_index=True, height=min(640, 38 + 35 * len(df)))
    elif path.suffix == ".md":
        with st.container(border=True, height=640):
            st.markdown(text)
    else:
        st.code(text, language=None, wrap_lines=True, height=640)


page()
