# Traceable Insight — Hack 1 MVP Design

Problem 09B, team HFMD Aur Samose (Hyderabad Runners Society, Project Champion).
Source plan: `hack1_prep.pdf`.

## Goal

One synthetic school (School A) run end to end: raw source files → coordinator view where every
child has exactly one state and every statement about the child links to the exact source line.

States, by precedence: **Conflict to review** > **Not enough information** > **Needs attention** >
**On track**. The tool flags and shows evidence; the coordinator decides. No scores or rankings of
children. Synthetic data only.

## Decisions

| Topic | Decision |
|---|---|
| Repo | New local git repo `traceable-insight/`, pushed to team repo later |
| UI | Streamlit (A8), styled per Apple HIG via `apple-design` skill |
| LLM | Ollama required. Default model `qwen3:4b` (`think: false`, JSON format, temperature 0, seed 7). Configurable via `TI_OLLAMA_MODEL`. Pipeline exits with a clear error if Ollama is unreachable |
| Python | 3.12 via uv |
| Store | SQLite (`var/ti.db`). Chroma deferred |

## Layout

```
src/ti/
  config.py        paths, model name, Ollama URL
  llm.py           Ollama client (generate JSON), disk cache keyed by sha256(model+prompt)
  generator/  A1   roster, profiles, structured, whatsapp, guideline, truth, cli
  ingest/     A2   parsers + pii
  extract/    A3   structured facts + LLM facts + span verification
  link/       A4   name matcher + review queue
  store/      A5   schema.sql, db helpers, thresholds loader
  state/      A6   rules
  queries.py       read layer shared by API and UI
  api/        A7   FastAPI
  score.py    #15
app/coordinator.py  A8
run_pipeline.py     #14
data/synthetic/school_a/   committed
var/                       gitignored (db, llm cache, score.json)
```

## A1 Synthetic data (seeded, `python -m ti.generator --seed 42`)

- Roster: 25 children (Class 6 and 7), coach "Coach Arjun Mehra" (fictional), PE teacher
  "Mrs. Lata Iyer" (fictional). Names randomly combined from public common-name lists.
  Two children share first name **Ravi** (Ravi Kumar, Ravi Shankar).
- Latent profile per child: attendance rate, fitness trend, planted condition.
  Planted: 4 conflict, 4 gap, 5 needs attention, 12 on track.
- Sessions: 12 (Tue/Fri across 6 weeks starting 2026-07-07).
- `attendance_wk{1..6}.csv`: wide sheet (`Name`, two date columns, values `P`/`A`/blank).
  The teacher writes some names as variants. Gap children have whole weeks missing.
- `coach_forms.csv`: one row per session — `Timestamp, Coach, Session date, Group, Notes`.
  Notes mention 3–5 children (praise, concern, participation). Conflict children are mentioned as
  participating on a date where attendance says `A`.
- `assessments.csv`: `round, date, name, sprint_50m_s, broad_jump_cm, run_600m_s`. Baseline
  (all 25) and midline (gap children missing). Needs-attention children decline beyond threshold.
- `whatsapp.txt`: Android export (`dd/mm/yy, h:mm am - Sender: text`), ~200 messages. Each
  message is first built from a template carrying its intended mentions (child_id + surface
  variant), then rewritten into Hinglish by Ollama. The rewrite must keep every surface variant
  verbatim; retry 3×, then raise. Includes off-topic messages, group references, phone numbers
  from fake range `+91 90000 0xxxx`, `<Media omitted>`, links. ~20% of mentions use variants;
  bare "ravi" appears at least twice.
- `guideline.md`: header "SYNTHETIC — placeholder thresholds, to be validated with HRS",
  ~30 short sections. Thresholds also in `thresholds.yaml`.
- `ground_truth.json`: roster states, every mention (file, ref, surface, child_id or
  `"ambiguous"`), planted conflicts, planted gaps.

## A2 Ingest

Each parser yields `SourceLine(source_file, ref, text, meta)`; `ref` is `row:N` or `msg:N`.
PII scrub replaces phone numbers with `[phone]`, URLs with `[link]`, drops `<Media omitted>`
messages. Scrubbed text is what is stored and cited.

## A3 Extract

- Structured (attendance, assessments): deterministic facts, quoted span = the cell value context
  (e.g. row text `Ravi K,P,A`).
- Free text (WhatsApp, coach notes): Ollama returns
  `{"facts":[{"name":..., "type": praise|concern|participation|injury|absence|other,
  "quote":..., "summary":...}]}`.
- **Span verification**: `quote` must be an exact substring of the stored line text; else the fact
  is dropped and counted in `rejected_facts`. Name string must also be a substring.
- Cached on disk so repeat runs are instant.

## A4 Link

Candidate keys per child: full name, first name, surname, first+surname initial.
Score = max(rapidfuzz `WRatio`, 100·Jaro-Winkler, metaphone-equal bonus).
- top ≥ 90 and lead over second ≥ 8 → linked
- otherwise top ≥ 70 → review queue (with candidates)
- otherwise unlinked
Group references (`class 6`, `boys`, `sab`, `all`) skipped. Coordinator can resolve queue items
in the UI (stored in `link_overrides`).

## A5 Store (SQLite)

Tables: `children`, `source_lines`, `mentions`, `facts`, `review_queue`, `link_overrides`,
`child_states`, `run_meta`. Every fact has `source_line_id` and `quote`.

## A6 State rules (`thresholds.yaml`)

- Conflict: a coach-form participation/praise fact for a date where attendance = `A`.
- Not enough info: recorded attendance sessions < 6 of 12, or no midline assessment.
- Needs attention: attendance rate < 0.60 over recorded sessions, or fitness decline (600m run
  slower by > 8% or sprint slower by > 8%), or ≥ 2 concern facts.
- On track otherwise.
Each state stores `reason` text and `evidence_fact_ids`.

## #14 / #15

`uv run python run_pipeline.py --school school_a` runs ingest → extract → link → state.
`uv run python -m ti.score` reports link accuracy (≥ 0.85), conflicts (≥ 3/4), gaps (≥ 3/4),
citations resolving (= 100%). Writes `var/score.json`.

## A7 API

`GET /schools/{id}`, `GET /children/{id}`, `GET /sources/{line_id}` — thin wrappers over
`queries.py`. Streamlit reads `queries.py` directly.

## A8 Coordinator view

Pages: School (four state groups, child cards: first name, class, one-line reason), Child
(state banner + cited facts; each fact expands to source line ±2 lines with quote highlighted),
Review queue, Check (live score). Theme via `.streamlit/config.toml` plus scoped CSS; system
font stack; semantic state colours valid in light and dark; state always shown with label and
icon, never colour alone.

## Testing

pytest per module. LLM paths use a fake client. `@pytest.mark.ollama` integration test runs the
real model. Generator determinism test (same seed → identical files).

## Out of scope (Sprint 3)

NLI citation check, cross-school reconciliation, fitness-by-school view, Chroma retrieval.
