"""PII scrub at ingest: nothing with a phone number, link or media reaches the store."""

import re

PHONE = re.compile(r"(?:\+91[\s-]?)?\b[6-9]\d{4}[\s-]?\d{5}\b")
URL = re.compile(r"https?://\S+|www\.\S+")
EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.]+\b")
MEDIA = {"<Media omitted>", "image omitted", "video omitted", "This message was deleted"}


def scrub(text: str) -> str | None:
    """Return scrubbed text, or None when the whole message is media or deleted."""
    if text.strip() in MEDIA:
        return None
    text = URL.sub("[link]", text)
    text = EMAIL.sub("[email]", text)
    return PHONE.sub("[phone]", text)
