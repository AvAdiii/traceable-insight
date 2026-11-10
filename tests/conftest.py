import pytest

from ti import config, db


@pytest.fixture(scope="session")
def workspace(tmp_path_factory):
    """A seeded demo store in a temp dir: synthetic workbooks -> full pipeline -> events."""
    root = tmp_path_factory.mktemp("ti")
    config.DEMO_DIR = root / "demo"
    config.UPLOAD_DIR = root / "uploads"
    config.VAR_DIR = root
    db.use(f"sqlite:///{root / 'ti.db'}")
    from ti import seed
    seed.seed(fresh=False)
    return root


@pytest.fixture()
def s(workspace):
    sess = db.session()
    yield sess
    sess.close()
