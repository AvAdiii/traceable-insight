# Product: Stride

<!-- impeccable:product-schema 1 -->

> Inferred from the 2026-11-10 brief; the user asked for no further questions. Facts marked
> *(inferred)* are unconfirmed.

## Platform

web

## Stack

Delegated: FastAPI + SQLAlchemy (SQLite locally, Postgres/Supabase hosted) and a React + Vite +
TypeScript PWA, phone first. In-browser LLM via WebLLM, with laptop Ollama and a rule parser as
fallbacks.

## Users

Primary: the Project Champion programme manager (coordinator) at Hyderabad Runners Society, who
oversees PT and sports sessions in many government schools. Also supervisor PTs (a few schools
each) and PT trainers (one school, fill the assessment sheet). They work on laptops and phones,
in the office and at school grounds *(inferred: often outdoors in daylight)*.

## Product Purpose

Turn the assessment spreadsheets PT trainers already fill into cited per-child insight: who is
strongest, who needs a push, who improved or declined on jump, throw, run and endurance; and pick
athletes for sports meets (school, zonal, district, state, the annual meet where about 1 in 7
children are shortlisted). Success: the manager finds the right children in seconds and can show
where every number came from.

## Positioning

Every number opens the exact spreadsheet cell it came from (file, sheet, cell), and data problems
are separated from children's performance: a placeholder, a duplicate or a wrong unit never
silently ranks a child.

## Operating Context

One fixed Excel template per school per round (baseline / midline / endline), filled by the PT
trainer and collected by a supervisor. No WhatsApp or paper sources. Sheets contain real typing
errors: duplicated blocks, pasted classes, placeholder values, wrong units, mixed date formats.

## Capabilities and Constraints

Upload and validate sheets; percentiles within gender and age, programme-wide; flags (top
performer, most improved, needs a push, declining, missing test); Inbox for data checks; schools
and coaches as filters; calendar of meets with items, AI shortlist with reasons and reserves,
confirmation, to-dos, results and achievements; Ask in plain language. Roles: manager, supervisor,
trainer. Undecided: real round cadence and baseline norms (to confirm with HRS).

## Evidence on Hand

Synthetic demo data generated on the real template (`data/demo/`), labelled synthetic. The real
HRS workbook contains children's personal data and must never be committed, published or sent to
a model.

## Product Principles

1. Cite everything: a number without its cell is not shown as fact.
2. Data problems are not children's problems: keep the Inbox apart from performance flags.
3. The tool suggests, the coordinator decides: shortlists are proposals with reasons.
4. Children's data stays with the programme: the language model never sees it.
5. Phone first, laptop equal.

## Accessibility & Inclusion

WCAG AA contrast, 44px touch targets, never colour alone for meaning, light and dark appearance,
works on low-end Android phones *(inferred)*.
