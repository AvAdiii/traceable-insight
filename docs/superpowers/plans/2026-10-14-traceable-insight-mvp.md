# Traceable Insight MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan
> task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** One synthetic school run end to end, raw files → Streamlit coordinator view with one state
per child and every fact cited to its source line.

**Architecture:** Seeded generator writes source files; pipeline ingests → extracts (rules + Ollama,
span-verified) → links names → assigns states into SQLite; Streamlit and FastAPI read through
`ti.queries`.

**Tech Stack:** Python 3.12, uv, pandas, rapidfuzz, jellyfish, httpx (Ollama REST), PyYAML,
SQLite, FastAPI, Streamlit, pytest.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-10-14-traceable-insight-design.md`.
- State precedence: Conflict to review > Not enough information > Needs attention > On track.
- Planted counts: 4 conflict, 4 gap, 5 needs attention, 12 on track; 25 children.
- Ollama required: model `qwen3:4b`, `think: false`, `format: json`, temperature 0, seed 7.
- Every stored fact: `source_line_id` + `quote` that is an exact substring of the line text.
- No scores or rankings of children in the UI. Synthetic data only. `var/` gitignored.
- Targets: link accuracy ≥ 0.85, conflicts ≥ 3/4, gaps ≥ 3/4, citations resolve 100%.

---

### Task 1: Scaffold + Ollama client (`ti.config`, `ti.llm`)
- Produces: `config.ROOT, DATA_DIR, VAR_DIR, MODEL, OLLAMA_URL`;
  `llm.OllamaClient.generate_json(prompt: str, system: str) -> dict` (disk cached, raises
  `OllamaUnavailable`); `llm.FakeClient(responses)` for tests.
- Tests: cache hit avoids second HTTP call; unreachable server raises `OllamaUnavailable`.
- Done when: `uv run pytest tests/test_llm.py` passes.

### Task 2: A1 generator — roster, profiles, structured sources, guideline, truth (#1, #2, #4, #5)
- Produces: `ti.generator.roster.build_roster(rng) -> list[Child]`,
  `profiles.assign_profiles(roster, rng) -> dict[id, Profile]`,
  `structured.write_attendance/forms/assessments(...)`, `guideline.write_guideline(dir)`,
  `truth.TruthLog` (records mentions), CLI `python -m ti.generator`.
- Tests: 25 children, two named Ravi; planted counts exact; same seed → byte-identical files;
  conflict child has form mention on a date marked `A`; gap child missing midline / weeks.

### Task 3: A1 WhatsApp generator (#3)
- Produces: `generator.whatsapp.write_chat(roster, profiles, truth, client, out, rng)`.
- Template → Ollama Hinglish rewrite; every surface variant must survive verbatim; 3 retries.
- Tests (FakeClient): variant-dropping rewrite triggers retry, then `RuntimeError`; ~200 msgs;
  includes fake phone, media, link, bare "ravi" ×2.

### Task 4: A2 ingest + PII (#6, #7)
- Produces: `ingest.SourceLine(source_file, ref, text, meta)`, `ingest.load_school(dir) -> list[SourceLine]`,
  `ingest.pii.scrub(text) -> str | None`.
- Tests: phone/link replaced, media dropped; multi-line WhatsApp messages joined; attendance
  wide sheet → one line per child row with dates in meta.

### Task 5: A5 store (#10)
- Produces: `store.db.connect(path)`, `store.db.init(conn)`, insert helpers, `store.thresholds.load()`.
- Tests: schema creates all tables; thresholds load from yaml.

### Task 6: A3 extract (#8)
- Produces: `extract.structured_facts(lines)`, `extract.llm_facts(lines, client)`,
  `extract.verify(fact, line) -> bool`. Fact dict keys: `line_id, name, type, quote, summary, date, value`.
- Tests: fabricated quote rejected; attendance row gives one fact per session.

### Task 7: A4 link (#9)
- Produces: `link.Matcher(roster).match(surface) -> MatchResult(status, child_id, score, candidates)`.
- Tests: "Ravi K" → Ravi Kumar linked; "ravi" → review; "Class 6 boys" → skipped; misspelling linked.

### Task 8: A6 state (#11)
- Produces: `state.assign_states(conn, thresholds) -> dict[child_id, State]`.
- Tests: synthetic facts per rule; precedence holds when a child meets two rules.

### Task 9: Pipeline + score (#14, #15)
- `run_pipeline.py --school school_a`; `ti.score` → `var/score.json`.
- Done when: real run with Ollama meets targets (or gaps documented).

### Task 10: A7 API + `ti.queries` (#12)
- Tests: FastAPI TestClient on school/child/source endpoints.

### Task 11: A8 Streamlit coordinator view (#13) + apple-design review
- Pages: School, Child, Review queue, Check. Verify by screenshot in browser, light and dark.

### Task 12: README, GitHub issue bodies (`docs/issues.md`), final verification.
