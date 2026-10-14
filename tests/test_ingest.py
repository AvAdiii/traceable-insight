from ti.ingest import load_roster, load_school
from ti.ingest.parsers import parse_whatsapp
from ti.ingest.pii import scrub


def test_scrub_phone_link_media():
    assert scrub("call +91 90000 01288 now") == "call [phone] now"
    assert scrub("call 9000001288") == "call [phone]"
    assert scrub("see https://forms.gle/x ok") == "see [link] ok"
    assert scrub("<Media omitted>") is None
    assert scrub("aaj 600m mein 182 sec") == "aaj 600m mein 182 sec"


def test_whatsapp_multiline_system_and_numbering(tmp_path):
    p = tmp_path / "whatsapp.txt"
    p.write_text(
        "07/07/26, 9:01 am - Messages and calls are end-to-end encrypted.\n"
        "07/07/26, 9:06 am - Coach: plan:\n1. warm up\n2. relay\n"
        "07/07/26, 9:07 am - +91 90000 07341: <Media omitted>\n"
        "07/07/26, 9:08 am - +91 90000 07341: Ravi K aaj nahi aayega\n")
    lines = parse_whatsapp(p)
    assert [l.ref for l in lines] == ["msg:1", "msg:3"]
    assert lines[0].text == "plan:\n1. warm up\n2. relay"
    assert lines[1].meta == {"date": "2026-07-07", "time": "9:08 am", "sender": "[phone]"}


def test_load_school_covers_every_source(school_dir):
    lines = load_school(school_dir)
    kinds = {l.kind for l in lines}
    assert kinds == {"attendance", "coach_form", "assessment", "whatsapp", "guideline"}
    assert len(load_roster(school_dir)) == 25
    att = [l for l in lines if l.kind == "attendance"]
    assert all(len(l.meta["marks"]) == 2 for l in att)
    wa = [l for l in lines if l.kind == "whatsapp"]
    assert not any("+91 90000" in l.text or "https://" in l.text for l in wa)
    assert len([l for l in lines if l.kind == "guideline"]) == 30
    # refs are unique per file
    keys = [(l.source_file, l.ref) for l in lines]
    assert len(keys) == len(set(keys))
