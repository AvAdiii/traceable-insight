"""Headless render of every coordinator page (Streamlit AppTest) against a fake-model run."""

import sys
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from ti import config, pipeline
from ti.llm import FakeClient
from tests.test_pipeline import names_in

APP = Path(__file__).resolve().parents[1] / "app"


@pytest.fixture(scope="module")
def app_env(school_dir, tmp_path_factory):
    db_path = tmp_path_factory.mktemp("app") / "school_t.db"
    pipeline.run("school_t", FakeClient(fn=names_in), db_path=db_path,
                 data_dir=school_dir.parent, log=lambda *_: None)
    mp = pytest.MonkeyPatch()
    mp.setattr(config, "db_path", lambda school: db_path)
    mp.setattr(config, "DATA_DIR", school_dir.parent)
    mp.setattr(config, "VAR_DIR", db_path.parent)
    sys.path.insert(0, str(APP))
    yield
    sys.path.remove(str(APP))
    mp.undo()


def run(page: str, **state) -> AppTest:
    at = AppTest.from_file(str(APP / page), default_timeout=30)
    at.session_state["school"] = "school_t"
    for k, v in state.items():
        at.session_state[k] = v
    return at.run()


@pytest.mark.parametrize("page", ["school.py", "review.py", "check.py"])
def test_page_renders_without_error(app_env, page):
    at = run(page)
    assert not at.exception, at.exception


def test_selecting_a_child_shows_their_detail(app_env):
    at = run("school.py")
    row_buttons = [b for b in at.button if b.key and b.key.startswith("btn-")]
    assert len(row_buttons) == 25
    row_buttons[-1].click().run()
    assert at.session_state["child"] == row_buttons[-1].key.removeprefix("btn-")
    assert not at.exception


def test_review_link_then_undo(app_env):
    at = run("review.py")
    radios = [r for r in at.radio if r.key and r.key.startswith("pick-")]
    if not radios:
        pytest.skip("fake run left nothing to review")
    mid = radios[0].key.removeprefix("pick-")
    from ti import queries
    from ti.store import db
    item = next(i for i in queries.review_queue(db.connect(config.db_path("school_t")))
                if str(i["mention_id"]) == mid)
    at.session_state[f"pick-{mid}"] = item["candidates"][0]["child_id"]
    at.run()
    at.button(key=f"link-{mid}").click().run()
    assert any(b.key == f"undo-{mid}" for b in at.button)
    assert not at.exception
    at.button(key=f"undo-{mid}").click().run()
    assert not at.exception
