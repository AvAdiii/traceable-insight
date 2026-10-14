SYSTEM = """You extract facts about individual CHILDREN from notes written by a school running coach or PE teacher in India. Text may be English or Hinglish (Hindi in Roman script).

For EVERY child mentioned BY NAME, output one fact, whatever is said about them. Names can be lowercase, misspelt or shortened, and some are also ordinary words (e.g. Bharat, Pooja, Lucky): if the word is used as a person, it is a child's name.
- "name": the child's name exactly as written in the text (same spelling and case, e.g. "Ravi K", "priyaa", "Ravikumar")
- "type": one of praise | participation | concern | injury | absence | other
    praise = did well, improved, focused, good effort
    participation = attended or took part, no judgement
    concern = tired, not interested, breathless, slower, worrying behaviour
    injury = pain, hurt, sprain
    absence = did not come, absent, nahi aaya / nahi aayi
    other = anything else said about the child (forms, questions, requests)
- "quote": the shortest exact span copied from the text that supports the fact, including the name
- "summary": a short plain-English sentence about the child

Do not output facts for adults (coach, teacher, sir, madam, parents) or for groups like "Class 6 boys" or "sab bacche".
If no child is named, return {"facts": []}.
Reply only with JSON: {"facts": [...]}"""

EXAMPLES = [
    ("Good session. Anjali S. ran well in the relay. vikky complained of knee pain.",
     '{"facts": [{"name": "Anjali S.", "type": "praise", "quote": "Anjali S. ran well in the '
     'relay", "summary": "Ran well in the relay."}, {"name": "vikky", "type": "injury", '
     '"quote": "vikky complained of knee pain", "summary": "Complained of knee pain."}]}'),
    ("aaj Bharat nahi aaya, koi update?",
     '{"facts": [{"name": "Bharat", "type": "absence", "quote": "Bharat nahi aaya", '
     '"summary": "Did not come today."}]}'),
    ("sunil ne abhi tak form nahi diya, please check karo",
     '{"facts": [{"name": "sunil", "type": "other", "quote": "sunil ne abhi tak form nahi '
     'diya", "summary": "Has not submitted the form yet."}]}'),
    ("Class 6 boys sab late aaye aaj", '{"facts": []}'),
]


def prompt(text: str) -> str:
    shots = "\n\n".join(f"Text: {i}\n{o}" for i, o in EXAMPLES)
    return f"{shots}\n\nText: {text}\n"
