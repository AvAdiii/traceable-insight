"""Traceable Insight coordinator view: `uv run streamlit run app/coordinator.py`."""

import streamlit as st

import ui
from ti import queries

st.set_page_config(page_title="Traceable Insight", page_icon=":material/fact_check:",
                   layout="wide", initial_sidebar_state="expanded")
st.session_state.setdefault("school", "school_a")
ui.inject_css()

c = ui.conn()
waiting = len(queries.review_queue(c)) if c else 0

children = st.Page("school.py", title="Children", icon=":material/groups:", default=True)
review = st.Page("review.py", title="Review names", icon=":material/person_search:",
                 url_path="review")
check = st.Page("check.py", title="Ground-truth check", icon=":material/rule:",
                url_path="check")

nav = st.navigation([children, review, check], position="hidden")

with st.sidebar:
    st.html("""<div class="brand"><div class="brand-t">Traceable Insight</div>
        <div class="eyebrow">Project Champion · synthetic data</div></div>""")
    st.page_link(children)
    st.page_link(review, label=f"Review names · {waiting} waiting" if waiting
                 else "Review names")
    st.page_link(check)

nav.run()
