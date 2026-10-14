import re

import pytest

from ti.llm import FakeClient


def echo_hinglish(prompt: str) -> dict:
    """Fake model: keeps the placeholders and adds a little Hinglish."""
    meaning = prompt.split("Meaning: ", 1)[1].split("\n")[0]
    return {"text": "aaj " + meaning.rstrip(".") + " hai"}


@pytest.fixture(autouse=True, scope="session")
def private_dir(tmp_path_factory):
    """Keep test runs' private copies out of the repo's data/private."""
    from ti import config
    mp = pytest.MonkeyPatch()
    mp.setattr(config, "PRIVATE_DIR", tmp_path_factory.mktemp("private"))
    yield config.PRIVATE_DIR
    mp.undo()


@pytest.fixture
def fake_llm():
    return FakeClient(fn=echo_hinglish)


@pytest.fixture(scope="session")
def school_dir(tmp_path_factory, private_dir):
    """One generated school, shared by tests that only read it."""
    from ti.generator.__main__ import generate
    root = tmp_path_factory.mktemp("data")
    generate("school_t", 42, FakeClient(fn=echo_hinglish), data_dir=root)
    return root / "school_t"
