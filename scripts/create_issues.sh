#!/usr/bin/env bash
# Create labels, milestones and issues 1-17 on the team repo.
# usage: scripts/create_issues.sh RCTS-IIITH/dsi-monsoon-2026-09b
set -euo pipefail
REPO="${1:?repo, e.g. RCTS-IIITH/dsi-monsoon-2026-09b}"

for l in "A1 Generator" "A2 Ingest" "A3 Extract" "A4 Link" "A5 Store" "A6 State" "A7 API" "A8 UI"; do
  gh label create "$l" --repo "$REPO" --force >/dev/null
done
for m in "Hackathon 1" "Sprint 3"; do
  gh api "repos/$REPO/milestones" -f title="$m" >/dev/null 2>&1 || true
done

# title|labels (comma separated)|milestone|priority|done when
while IFS='|' read -r title labels milestone priority done; do
  [ -z "$title" ] && continue
  args=()
  IFS=',' read -ra ls <<< "$labels"
  for l in "${ls[@]}"; do args+=(--label "$l"); done
  body=$(printf '**Component:** %s\n**Priority:** %s\n**Done when:** %s\n' "$labels" "$priority" "$done")
  gh issue create --repo "$REPO" --title "$title" --milestone "$milestone" "${args[@]}" --body "$body"
done <<'ISSUES'
[A1] Define schemas and School A roster (25 fictional children, 1 coach, 1 PE teacher)|A1 Generator|Hackathon 1|Must|roster.csv has 25 children with exactly one shared first name; schemas documented
[A1] Generate attendance, coach forms and assessments from the roster|A1 Generator|Hackathon 1|Must|6 weekly sheets, 12 forms, 2 assessment rounds; same seed gives identical files
[A1] Generate Hinglish WhatsApp chat with name variants, fictional names and phone numbers|A1 Generator|Hackathon 1|Must|~200 messages, ~20% variant mentions, planted names survive the rewrite verbatim
[A1] Write ground_truth.json for planted cases|A1 Generator|Hackathon 1|Must|every mention, conflict and gap logged; the pipeline never reads it
[A1] Write the synthetic programme guideline with thresholds, marked as synthetic|A1 Generator|Hackathon 1|Must|guideline.md and thresholds.yaml exist and are marked synthetic
[A2] Parsers for WhatsApp, attendance CSV and form exports|A2 Ingest|Hackathon 1|Must|every source parses into lines with stable row/msg refs
[A2] PII scrub at ingest: phone numbers, media and links|A2 Ingest|Hackathon 1|Should|no phone numbers, links or media reach the store
[A3] Extract per-child facts with quoted source span (local Ollama model)|A3 Extract|Hackathon 1|Must|every stored quote is an exact substring of its source line
[A4] Name matcher with confidence threshold and review queue|A4 Link|Hackathon 1|Must|>= 85% of mentions linked correctly; shared first names go to review
[A5] SQLite schema and guideline thresholds file (Chroma index only if time allows)|A5 Store|Hackathon 1|Must|schema rebuilds per run and coordinator overrides survive
[A6] State rules for the four child states|A6 State|Hackathon 1|Must|one state per child by precedence, with evidence and guideline section
[A7] Thin FastAPI endpoints for school, child facts and source lookup|A7 API|Hackathon 1|Should|school, child, source and review endpoints tested
[A8] Minimal coordinator view mirroring the Figma school and child screens|A8 UI|Hackathon 1|Must|school view, child view with cited facts, source viewer, review queue
[A2-A6] run_pipeline.py one-command run for one school|A2 Ingest,A3 Extract,A4 Link,A5 Store,A6 State|Hackathon 1|Must|one command runs ingest to state and prints the check
[A4, A6] Score pipeline against ground_truth.json|A4 Link,A6 State|Hackathon 1|Must|link accuracy, conflicts, gaps and citations reported against targets
[A8] Fitness by school view from assessment data|A8 UI|Sprint 3|Later|to be defined in Sprint 3
[A3] NLI citation check on every extracted fact|A3 Extract|Sprint 3|Later|to be defined in Sprint 3
ISSUES
