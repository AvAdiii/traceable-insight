# Data schemas (issue #1)

All files are synthetic and written by `python -m ti.generator` (seeded). One folder per
school under `data/synthetic/<school>/`; programme-wide files under `data/synthetic/programme/`.

## Source files (what the pipeline reads)

| File | Rows (School A) | Columns / format | Written by |
|---|---|---|---|
| `roster.csv` | 25 | `child_id, first, surname, class, age, gender` | programme |
| `staff.csv` | 2 | `role, name, note` (1 coach, 1 PE teacher, both fictional) | programme |
| `attendance_wk{1..6}.csv` | 6 × 50 = 300 | `Date (dd-mm-yyyy), Day, Student name, Status` with Status `P`, `A` or blank (not recorded) | PE teacher |
| `coach_forms.csv` | 12 | `Timestamp, Coach name, Session date, Group, Who stood out / any concerns?` (free text naming 3–5 children) | coach, Google Form export |
| `assessments.csv` | 2 × 25 = 50 | `Round (baseline/midline), Date, Student name, 50m sprint (s), Standing broad jump (cm), 600m run (s)`; results blank when the child was not tested | PE teacher |
| `whatsapp.txt` | ~215 messages | Android export: `dd/mm/yy, h:mm am - Sender: text`; continuation lines belong to the previous message; system lines have no `Sender:` | school group |
| `../programme/guideline.md` | 30 sections | Markdown, one `## n. Title` per chunk, marked SYNTHETIC | programme |
| `../programme/thresholds.yaml` | 1 | `min_recorded_sessions, require_midline_assessment, attendance_rate_min, fitness_decline_pct, concern_mentions_min` | programme |

Names in sheets and messages are written the way people write them: first names, initials
("Ravi K."), typing slips ("Omanaa"), nicknames in chat ("Vicky"), lowercase ("ravi").

## Ground truth (read only by `ti.score`)

`ground_truth.json`:

```
children[]            roster row + condition, kind, expected_state
planted_conflicts[]   {child_id, date, rule}
planted_gaps[]        {child_id, kind: missing_weeks | no_midline}
mentions[]            {file, ref, surface, child_id | "ambiguous", variant}
planted_facts[]       {child_id, kind, file, ref, date}
noise                 {name_variants, missing_weeks, missing_assessments,
                       late_entries, contradictory_reports}
```

## References

Every source line has a stable reference: `row:N` (1-based data row of a CSV), `msg:N` (N-th
sender message in the chat, counting messages the PII scrub drops), `sec:N` (guideline
section).

## Evidence store (`var/<school>.db`, SQLite, git-ignored)

| Table | Purpose |
|---|---|
| `children` | roster |
| `source_lines` | every scrubbed source line; linked names replaced by roster ids, e.g. `[A03]` |
| `mentions` | every name occurrence: surface, status (`linked`, `review`, `unlinked`, `override`), child, score, candidates |
| `facts` | one cited statement: line, child, type, date, quote (exact substring of the line), summary |
| `child_states` | one state per child, reasons, evidence fact ids, guideline sections |
| `link_overrides` | coordinator decisions from the review queue; kept across re-runs |
| `run_meta` | counts, model, time, path of the private copy |

The original wording of each line and quote is kept in `data/private/<school>/originals.json`
(git-ignored) so citations can still open the exact source line.
