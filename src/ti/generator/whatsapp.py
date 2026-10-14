"""School WhatsApp group, Android export format.

Child-mention messages start as an English "meaning" built from the latent profile, then a
local model rewrites them into Hinglish. The exact name strings (the planted variants) must
survive the rewrite or the message is retried, then the run fails: ground truth stays exact.
"""

import datetime as dt
import random
import re
from dataclasses import dataclass, field
from pathlib import Path

from ti.generator import names
from ti.generator.profiles import sessions
from ti.generator.roster import COACH, COORDINATOR, PE_TEACHER
from ti.generator.truth import TruthLog

FNAME = "whatsapp.txt"
UNSAVED = "+91 90000 07341"  # fake reserved-range number of a parent volunteer

SYSTEM = """You write WhatsApp messages for a SYNTHETIC test dataset about a school running programme in Hyderabad.
Style: casual Hinglish in Roman script (Hindi + English mixed), short, like a busy coach or teacher typing on a phone. Talk ABOUT the children, never to them. Keep the meaning.
Children are written as placeholders like @1 and @2. Copy every placeholder into your text exactly once, unchanged. Do not add any names.
Reply only with JSON: {"text": "..."}

Example
Meaning: @1 did very well in the sprint today.
{"text": "aaj sprint mein @1 ne kamaal kar diya, bahut fast thi"}

Example
Meaning: @1 and @2 did not come to practice.
{"text": "@1 aur @2 aaj practice pe nahi aaye, koi update?"}"""

MEANINGS = {
    "praise": [
        "{n} ran really well in today's relay.",
        "{n} has improved a lot, very good effort today.",
        "{n} was the most focused one in drills today.",
        "{n} finished the 600m loop without stopping today, good progress.",
        "{n} was first in the 50m sprint today.",
        "{n} is showing much better stamina now.",
        "{n} kept running till the end even when tired, very good attitude.",
    ],
    "participation": [
        "{n} did the full session today.",
        "{n} joined all the drills today.",
        "{n} came on time and did warm up properly today.",
        "{n} did the stretching and relay today.",
    ],
    "concern": [
        "{n} was complaining of leg pain after the run today, please check.",
        "{n} looked very tired and sat down in the middle of the session.",
        "{n} is not taking interest in running these days, can someone talk to the parents?",
        "{n} was breathless very early today, worried.",
    ],
    "absence": [
        "{n} did not come for today's session.",
        "{n} is absent again today.",
        "{n} was absent today, parents said fever.",
    ],
}

# Messages without child mentions: written directly in Hinglish (no model needed).
CHATTER = {
    COORDINATOR: [
        "Good morning everyone 🙏", "Is week ka attendance sheet Friday tak bhej dena please",
        "Coach form har session ke baad fill karna hai, reminder", "Thank you sir 🙏",
        "Kal HRS visit hai, 7 baje tak ground pe rehna", "Noted", "Ok sir",
        "Midline test ki date fix karo please", "Water bottles ka stock check karo",
        "Sab schools ka update weekend tak chahiye", "Great work team 👏",
        "Kisi ko kuch chahiye toh batana", "Next week HRS ka photographer aayega",
        "Form link: https://forms.gle/synthetic-hrs-coach-form",
    ],
    COACH: [
        "Good morning", "Ground pe paani bhara hai, aaj indoor stretching karenge",
        "Aaj thoda late start hoga, 7:15", "Relay batons mil gaye 👍",
        "Kal baarish ka forecast hai", "Ok madam", "Done", "<Media omitted>",
        "Class 6 boys sab late aaye aaj", "Class 7 girls ne accha kiya aaj relay mein",
        "Sab bachon ko bolo shoes pehen ke aaye", "Location: https://maps.app.goo.gl/synthGround42",
        "Mera naya number +91 90000 01288, isse call karna", "Cones kisi ne dekhe? 2 missing hain",
        "Aaj ka session accha gaya 👍", "Kal 600m practice karenge", "Stopwatch ki battery khatam",
        "Sab ko paani ki bottle lana zaroori hai", "Class 6 girls ko relay mein aur practice chahiye",
        "Video dekho: https://youtu.be/synthetic-warmup-drills",
    ],
    PE_TEACHER: [
        "Attendance sheet bhej diya", "<Media omitted>", "Ok sir", "Kal school mein exam hai, "
        "session 30 min ka hi hoga", "Ground ki chaabi watchman ke paas hai", "Noted 👍",
        "Sab bacche thak gaye the aaj, garmi bahut thi", "Class 6 ka PT period shift ho gaya",
        "Thank you coach", "Sports day ki list banana hai",
    ],
    UNSAVED: [
        "Sir mera beta kal nahi aa payega", "Kitne baje khatam hota hai session?",
        "<Media omitted>", "Thank you sir 🙏",
    ],
}

MULTILINE = [
    (COACH, "Friday plan:\n1. warm up 10 min\n2. sprint drills\n3. relay\n4. stretching"),
    (COORDINATOR, "Reminders for this week:\n- attendance sheet by Friday\n- coach form after "
                  "every session\n- no photos with names please"),
]


@dataclass
class Draft:
    when: dt.datetime
    sender: str
    text: str = ""                       # final text (set directly or by rewrite)
    meaning: str = ""                    # English meaning for the model
    mentions: list = field(default_factory=list)   # (surface, child_id or "ambiguous")
    facts: list = field(default_factory=list)      # (child_id, kind)


def _ts(day: dt.date, rng: random.Random, lo=6, hi=21) -> dt.datetime:
    return dt.datetime.combine(day, dt.time(rng.randint(lo, hi), rng.randint(0, 59)))


def fmt_time(t: dt.datetime) -> str:
    h = t.hour % 12 or 12
    return f"{t:%d/%m/%y}, {h}:{t:%M} {'am' if t.hour < 12 else 'pm'}"


def plan_messages(roster, profiles, rng: random.Random, concern_left: dict) -> list[Draft]:
    drafts: list[Draft] = []
    by_id = {c.child_id: c for c in roster}
    days = sessions()

    def mention(cid, kind, day, sender=COACH, rate=0.25):
        c = by_id[cid]
        n = names.surface(c.first, c.surname, rng, rate=rate)
        d = Draft(_ts(day, rng, 8, 21), sender,
                  meaning=rng.choice(MEANINGS[kind]).format(n=n))
        d.mentions.append((n, cid))
        d.facts.append((cid, kind))
        drafts.append(d)

    for day in days:
        present = [c.child_id for c in roster if profiles[c.child_id].present.get(day) is True]
        absent = [c.child_id for c in roster if profiles[c.child_id].present.get(day) is False]
        for cid in rng.sample(present, k=min(len(present), rng.randint(3, 5))):
            mention(cid, rng.choice(["praise", "praise", "participation"]), day)
        for cid in absent:
            p = profiles[cid]
            if p.conflict_date == day:
                continue  # keep the conflict between form and sheet, not the chat
            want = 0.8 if p.kind == "low_attendance" else 0.25
            if rng.random() < want:
                mention(cid, "absence", day, sender=PE_TEACHER)
        # two children in one message, now and then
        if len(present) >= 2 and rng.random() < 0.4:
            a, b = rng.sample(present, 2)
            ca, cb = by_id[a], by_id[b]
            na = names.surface(ca.first, ca.surname, rng)
            nb = names.surface(cb.first, cb.surname, rng)
            d = Draft(_ts(day, rng, 8, 20), COACH,
                      meaning=f"{na} and {nb} both did very well in the relay today.")
            d.mentions += [(na, a), (nb, b)]
            d.facts += [(a, "praise"), (b, "praise")]
            drafts.append(d)

    # Remaining planted concerns go to the chat, on days the child was present.
    for cid, left in concern_left.items():
        days_present = [d for d, v in profiles[cid].present.items() if v]
        for day in rng.sample(days_present, k=min(left, len(days_present))):
            mention(cid, "concern", day)
        concern_left[cid] = 0

    # Fitness decline shows up in the chat after midline as an observation, not a rule input.
    for c in roster:
        if profiles[c.child_id].kind == "fitness_decline":
            n = names.surface(c.first, c.surname, rng, rate=0)
            d = Draft(_ts(days[-1], rng, 17, 21), PE_TEACHER,
                      meaning=f"{n}'s 600m time in the midline test is much slower than "
                              f"in the baseline.")
            d.mentions.append((n, c.child_id))
            d.facts.append((c.child_id, "concern"))
            drafts.append(d)

    # Demo step 5: the same child written two different ways, both must resolve to one child.
    rk = next(c for c in roster if c.full == "Ravi Kumar")
    rk_present = [d for d, v in profiles[rk.child_id].present.items() if v]
    for surface, kind in [("Ravi K", "praise"), ("Ravikumar", "participation")]:
        day = rk_present[len(drafts) % len(rk_present)]
        d = Draft(_ts(day, rng, 8, 21), COACH,
                  meaning=rng.choice(MEANINGS[kind]).format(n=surface))
        d.mentions.append((surface, rk.child_id))
        d.facts.append((rk.child_id, kind))
        drafts.append(d)

    # Bare "ravi": two children share the name, so these must go to the review queue.
    for day, sender, meaning in [
        (days[3], COORDINATOR, "ravi did not submit the consent form yet, please follow up."),
        (days[8], COACH, "ravi was asking whether he can join the district run."),
    ]:
        d = Draft(_ts(day, rng, 9, 20), sender, meaning=meaning)
        d.mentions.append(("ravi", "ambiguous"))
        drafts.append(d)

    # Chatter, including PII the ingest step must scrub.
    all_days = [days[0] + dt.timedelta(days=i) for i in range((days[-1] - days[0]).days + 1)]
    for sender, lines in CHATTER.items():
        for text in lines:
            for _ in range(3 if sender != UNSAVED else 1):
                drafts.append(Draft(_ts(rng.choice(all_days), rng), sender, text=text))
    for sender, text in MULTILINE:
        drafts.append(Draft(_ts(rng.choice(all_days), rng), sender, text=text))
    return drafts


def _ok(text: str, n: int, other_firsts: set[str]) -> bool:
    if not text or len(text) > 320:
        return False
    if any(text.count(f"@{i}") != 1 for i in range(1, n + 1)) or f"@{n + 1}" in text:
        return False
    words = set(re.findall(r"[A-Za-z]+", text.lower()))
    return not (words & other_firsts)


def rewrite(d: Draft, client, roster) -> str:
    """Rewrite the meaning into Hinglish. Names are hidden behind @1, @2 so the model cannot
    'fix' a planted misspelling; they are put back verbatim afterwards."""
    meaning = d.meaning
    for i, (surface, _) in enumerate(d.mentions, 1):
        meaning = meaning.replace(surface, f"@{i}", 1)
    other = {c.first.lower() for c in roster}
    prompt = f"Meaning: {meaning}"
    for attempt in range(3):
        p = prompt if attempt == 0 else prompt + f"\n(Attempt {attempt + 1}: copy each @ placeholder exactly once.)"
        text = str(client.generate_json(p, SYSTEM).get("text", "")).strip().replace("\n", " ")
        if _ok(text, len(d.mentions), other):
            # Replace from the highest index down so @1 never clobbers @10.
            for i in range(len(d.mentions), 0, -1):
                text = text.replace(f"@{i}", d.mentions[i - 1][0])
            return text
    raise RuntimeError(f"Model could not keep placeholders for: {d.meaning}")


def write_chat(out: Path, roster, profiles, truth: TruthLog, client, rng: random.Random,
               concern_left: dict) -> int:
    drafts = plan_messages(roster, profiles, rng, concern_left)
    drafts.sort(key=lambda d: (d.when, d.sender, d.text, d.meaning))
    lines = []
    for i, d in enumerate(drafts, 1):
        if d.meaning:
            d.text = rewrite(d, client, roster)
        for surface, cid in d.mentions:
            truth.mention(FNAME, f"msg:{i}", surface, cid)
        for cid, kind in d.facts:
            truth.fact(cid, kind, FNAME, f"msg:{i}", d.when.date().isoformat())
        lines.append(f"{fmt_time(d.when)} - {d.sender}: {d.text}")
    header = (f"{fmt_time(drafts[0].when - dt.timedelta(minutes=5))} - Messages and calls are "
              f"end-to-end encrypted. No one outside of this chat can read or listen to them.")
    (out / FNAME).write_text("\n".join([header] + lines) + "\n")
    return len(drafts)
