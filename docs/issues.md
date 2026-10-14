# GitHub issues (Hackathon 1 + Sprint 3)

Labels: `A1 Generator` … `A8 UI`. Milestones: `Hackathon 1`, `Sprint 3`.
Each title starts with its tag. `scripts/create_issues.sh` creates these with `gh`.

| # | Title | Label | Priority | Milestone | Done when | Status |
|---|---|---|---|---|---|---|
| 1 | [A1] Define schemas and School A roster (25 fictional children, 1 coach, 1 PE teacher) | A1 Generator | Must | Hackathon 1 | `roster.csv` has 25 children with exactly one shared first name; schemas in spec | Done |
| 2 | [A1] Generate attendance, coach forms and assessments from the roster | A1 Generator | Must | Hackathon 1 | 6 weekly sheets, 12 forms, 2 assessment rounds; same seed → same bytes | Done |
| 3 | [A1] Generate Hinglish WhatsApp chat with name variants, fictional names and phone numbers | A1 Generator | Must | Hackathon 1 | ~200 messages, ~20% variant mentions, planted names survive the rewrite verbatim | Done |
| 4 | [A1] Write ground_truth.json for planted cases | A1 Generator | Must | Hackathon 1 | every mention, conflict and gap logged; pipeline never reads it | Done |
| 5 | [A1] Write the synthetic programme guideline with thresholds, marked as synthetic | A1 Generator | Must | Hackathon 1 | `guideline.md` (30 sections) + `thresholds.yaml`, both marked synthetic | Done |
| 6 | [A2] Parsers for WhatsApp, attendance CSV and form exports | A2 Ingest | Must | Hackathon 1 | every source → SourceLines with stable `row:N` / `msg:N` refs | Done |
| 7 | [A2] PII scrub at ingest: phone numbers, media and links | A2 Ingest | Should | Hackathon 1 | no phone/link/media text in the store (tested) | Done |
| 8 | [A3] Extract per-child facts with quoted source span (local Ollama model) | A3 Extract | Must | Hackathon 1 | every stored quote is an exact substring of its line | Done |
| 9 | [A4] Name matcher with confidence threshold and review queue | A4 Link | Must | Hackathon 1 | ≥ 85% mentions linked correctly; shared first name → review | Done |
| 10 | [A5] SQLite schema and guideline thresholds file (Chroma index only if time allows) | A5 Store | Must | Hackathon 1 | schema rebuilds per run; overrides survive | Done (Chroma deferred) |
| 11 | [A6] State rules for the four child states | A6 State | Must | Hackathon 1 | one state per child by precedence, with evidence and guideline section | Done |
| 12 | [A7] Thin FastAPI endpoints for school, child facts and source lookup | A7 API | Should | Hackathon 1 | 4 endpoints tested with TestClient | Done |
| 13 | [A8] Minimal coordinator view mirroring the Figma school and child screens | A8 UI | Must | Hackathon 1 | school view, child view, source viewer, review queue, check page | Done |
| 14 | [A2–A6] run_pipeline.py one-command run for one school | A2–A6 | Must | Hackathon 1 | one command runs ingest → state and prints the check | Done |
| 15 | [A4, A6] Score pipeline against ground_truth.json | A4, A6 | Must | Hackathon 1 | link accuracy, conflicts, gaps, citations reported vs targets | Done |
| 16 | [A8] Fitness by school view from assessment data | A8 UI | Later | Sprint 3 | — | Open |
| 17 | [A3] NLI citation check on every extracted fact | A3 Extract | Later | Sprint 3 | — | Open |
