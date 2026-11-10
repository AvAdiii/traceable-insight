from sqlalchemy import func, select

from ti import pipeline, verify
from ti.db import Flag, Issue, Measurement


def test_linking_matches_ground_truth(workspace):
    r = verify.report(verbose=False)
    assert r["children_found"] == r["children_true"]
    assert r["split_children"] == 0 and r["merged_children"] == 0


def test_planted_sheet_problems_reach_the_inbox(s):
    kinds = {k for (k,) in s.execute(select(Issue.kind))}
    assert {"class_copy", "placeholder", "unit", "conflict", "duplicate_rows", "sheet_disagree",
            "outlier", "implausible", "name", "dob"} <= kinds


def test_suspect_values_never_get_a_percentile(s):
    held = s.scalar(select(func.count()).select_from(Measurement).where(
        Measurement.status.in_(["suspect", "disputed"]), Measurement.percentile.is_not(None)))
    assert held == 0


def test_flags_are_many_per_child_not_one_bin(s):
    kinds = {k for (k,) in s.execute(select(Flag.kind))}
    assert kinds == {"top", "improved", "push", "declining", "missing"}


def test_decision_and_undo_round_trip(s):
    ph = s.scalar(select(Issue).where(Issue.kind == "placeholder"))
    key = ph.key
    pipeline.resolve(s, key, {"accept": True})
    assert s.scalar(select(Issue).where(Issue.key == key)).resolved
    pipeline.undo(s, key)
    assert not s.scalar(select(Issue).where(Issue.key == key)).resolved


def test_same_file_twice_is_refused(s, workspace):
    from ti import config
    f = next(config.DEMO_DIR.glob("*Midline*.xlsx"))
    up = s.execute(select(Issue.upload_id)).first()
    import pytest
    from ti.db import Upload
    rid = s.scalar(select(Upload.round_id).where(Upload.filename == f.name))
    with pytest.raises(pipeline.Refused):
        pipeline.ingest_upload(s, f.read_bytes(), f.name, rid)
    s.rollback()
