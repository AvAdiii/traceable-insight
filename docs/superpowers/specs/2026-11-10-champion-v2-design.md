# Traceable Insight v2 — design (post mid-eval)

**Problem statement (to validate with HRS).** The Project Champion programme manager needs to see,
across all schools and coaches, which children are the strongest and which need a push on the
three core motor skills (jump, throw, run) and endurance, and to pick athletes for sports meets,
using only the assessment spreadsheets PT trainers already fill — with every number traceable to
its spreadsheet cell.

## Decisions (from the 2026-11-10 session)

| Topic | Decision |
|---|---|
| Rounds | One file per round (baseline / midline / endline / custom), round + test date chosen on upload. Synthetic data has three rounds. Confirm with HRS at the fortnightly check-in. |
| Ranking | Percentile per test within the same gender and age (at test date), programme-wide; direction aware (shuttle and relay: lower is better). Composite = weighted mean, weights adjustable. Filters: school, coach, class, gender, age, test, round, flag. |
| Hosting | Hosted: FastAPI API + Postgres (Supabase) in production, SQLite locally. Own JWT auth with roles (manager, supervisor, trainer). |
| LLM | In the browser (WebLLM, small Qwen model, JSON-schema constrained). Fallback chain: browser model → laptop Ollama → server rule parser. The model only turns a question into a structured query; answers are computed from cited cells. Children's data never goes to a model. |
| Meets | Full loop: calendar, events with items (discipline, gender, age band, slots), AI shortlist with cited reasons and reserves, coordinator confirms, to-do checklist, results → achievements. |
| Coach | Template has no coach column: Settings maps school → PT trainer → supervisor; uploads are stamped with the uploader. |
| Privacy | The real HRS workbook is never committed or published. The repo ships a synthetic generator on the exact template with the real error types planted. |

## Architecture

```
Excel upload ─► uploads (file version, SHA-256, stored file)
   │
   ├─ ingest   read every template sheet, map headers, keep raw cells (sheet, row, column)
   ├─ clean    ok / repaired / suspect / missing, raw + reason kept
   ├─ checks   duplicates, copied class blocks, placeholders, zeros, implausible values,
   │           malformed DOB, sheet disagreement, unit mismatch  → Inbox
   ├─ identity school + name + parent + DOB, initials-aware fuzzy match → children registry
   ├─ score    percentile within gender × age, composite
   └─ flags    top performer, most improved, needs a push, declining, missing test
                       │
             read layer (ti.queries) ─► FastAPI ─► React PWA (phone first)
                                                   └─ WebLLM worker (Ask, shortlist questions)
```

Persistent (never rebuilt): users, schools/coach mapping, uploads + stored files, records, children
registry and aliases, coordinator resolutions, events / items / selections / results / todos,
settings. Derived (rebuilt after every upload or resolution): measurements, scores, flags, issues.

## Flags vs. Inbox

Child flags describe performance and may stack: Top performer, Most improved, Needs a push,
Declining, Missing test. Data problems are not child categories: they go to the Inbox (Entry to
check, Name to confirm) and suspect values are excluded from rankings and shortlists until the
coordinator accepts or corrects them.

## Screens

Home (KPIs, progress chart, upcoming events, top performers, inbox count) · Children (search,
filters, leaderboard by test) · Child profile (skill percentiles, rounds trend, achievements, every
number opens its cell) · Schools (per-school and per-coach comparison) · Calendar (month + agenda,
event detail: items, AI shortlist, confirm, to-dos, results) · Ask · Inbox · Upload · Settings.

Phone: bottom tab bar. Desktop: floating pill navigation. Flat surfaces, no emoji or gradients,
unDraw flat illustrations (references: NRDN, OCNUM). Apple HIG: system font, 44px targets,
light/dark, no colour-only meaning.
