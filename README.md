# Stride

*Traceable Insight for Project Champion: every number traced to its spreadsheet cell.*

**Problem 09B · Team HFMD Aur Samose · Hyderabad Runners Society, Project Champion**

> The Project Champion programme manager needs to see, across every school and coach, which
> children are strongest and which need a push on jump, throw, run and endurance, and to pick
> athletes for sports meets, using only the assessment sheets PT trainers already fill, with every
> number traceable to its spreadsheet cell. *(To validate with HRS at the next check-in.)*

v2 replaces the mid-eval prototype (Streamlit, synthetic WhatsApp and attendance sources, four
fixed child states) after feedback from Prof. Ramesh and the HRS representative.

## What changed since mid-eval

| Feedback | v2 answer |
|---|---|
| Real data is one Excel template, not WhatsApp/attendance | Parser for the HRS template (`Name of the School … Broard Jump … Relay Run Edurance Challenge`), cell-level citations (file › sheet › cell). WhatsApp generator and free-text LLM extraction removed. |
| Attendance is not the metric; motor skills are | Percentile per test (jump, run, throw, endurance) within the same gender and age, programme-wide, plus a weighted overall score. Progress across rounds in raw units. |
| Four exclusive states were wrong | Stackable flags: Top performer, Most improved, Needs a push, Declining, Missing test. Data problems live in a separate Inbox and never become a child's category. |
| Wrong level of the organisation | Manager / supervisor / trainer roles; school and coach are first-class filters. |
| Sports meets | Calendar, meets with races (discipline, gender, age band, places), AI shortlist with cited reasons and reserves, picks, to-dos, results → achievements, CSV team list. |
| Deliverable | Installable PWA, phone first, same app on laptop. |

## Run it (one command, synthetic data)

```bash
git clone https://github.com/RCTS-IIITH/dsi-monsoon-2026-09b && cd dsi-monsoon-2026-09b
docker compose up --build        # app + Postgres 16; first start seeds the demo (~1 min)
# open http://localhost:8000 (or http://<laptop-ip>:8000 on a phone on the same Wi-Fi)
```

Demo logins (password `champion`):

| Login | Sees |
|---|---|
| `manager@champion.demo` | programme manager, every school, uploads, Inbox decisions |
| `supervisor@champion.demo` | supervisor PT, their schools, meets and shortlists |
| `trainer@champion.demo` | PT trainer, only their schools |

- Data lives in named volumes (`pgdata`, `uploads`), so `docker compose down` / `up` keeps it.
  `docker compose down -v` wipes it and the next start seeds the demo again.
- Laptop model for Ask (optional): `docker compose --profile ollama up --build`, then
  `docker compose exec ollama ollama pull qwen2.5:3b`. Without it Ask uses the in-browser model
  (WebGPU) or the server rule parser.
- Without compose: `docker build -t stride . && docker run -p 8000:8000 stride` (SQLite inside
  the container, data lost when the container is removed).

### Configuration

Copy `.env.example` to `.env`; every value has a working demo default.

| Variable | Default | Meaning |
|---|---|---|
| `TI_DATABASE_URL` | `sqlite:///var/ti.db` (compose: the `db` Postgres) | SQLAlchemy URL; Postgres is `postgresql+psycopg://user:pass@host:5432/db` |
| `TI_SECRET` | demo value | signs login tokens; set a long random value when hosted |
| `TI_UPLOADS` | `var/uploads` (compose: `/data/uploads` volume) | where uploaded workbooks are stored |
| `TI_CORS` | `http://localhost:5173` (image: empty) | extra origins allowed to call the API |
| `POSTGRES_USER` / `_PASSWORD` / `_DB` | `stride` | compose Postgres credentials |
| `PORT` | `8000` | host port |

### Docker layout

- `Dockerfile`: three stages. Node builds the PWA; Python + uv installs the locked dependencies;
  the slim runtime copies only the virtualenv, `web/dist` and the synthetic `data/demo`, runs as
  the non-root user `stride`, and has a `HEALTHCHECK` on `/api/health`.
- `docker-compose.yml`: `app` waits for `db` (Postgres 16, `pg_isready` healthcheck); `ollama` is
  behind a profile.
- `.dockerignore` keeps `var/`, `data/private/`, any non-demo `.xlsx`, `.env` and git history out
  of the image.
- First run: `python -m ti.seed` loads the demo only when there are no users yet, then uvicorn starts.
- CI (`.github/workflows/ci.yml`) on every pull request and push to `main`: pytest, `vite build`,
  image build and a container health probe.
- Hosted demo: the same image on Render (`render.yaml`) with managed Postgres in `TI_DATABASE_URL`.

### Without Docker (development)

```bash
./dev.sh                 # uv sync, npm install, seed demo, API :8000 + web :5173 with hot reload
# open http://localhost:5173
```

Pieces on their own:

```bash
uv run python -m ti.generator          # write data/demo/*.xlsx (+ ground_truth.json)
uv run python -m ti.seed --fresh       # rebuild var/ti.db through the real pipeline
uv run python -m ti.verify             # score linking and planted issues against ground truth
uv run uvicorn ti.api:app --reload     # API (serves web/dist at / when built)
cd web && npm run dev                  # PWA dev server with /api proxy
uv run pytest                          # tests
```

## How it works

```
Excel upload (any device) ─► uploads: file version, SHA-256, stored file, round + test date
   ingest    find template sheets by header, keep every raw cell with its address;
             prefer a "Revised" sheet and pair each row with its twin in the other sheet
   clean     ok / repaired ("17kh" → 17, ".12.25", "5..84", number shown as a date) /
             suspect (out of range, with a unit hint) / missing (blank, 0)
   checks    repeated blocks, class block pasted into another class, placeholder values
             (one value for most of a school), relay in levels not seconds, sheets disagreeing,
             unusual for age (robust z within gender ± 1 year), DOB that does not fit the class
   identity  initials- and order-aware names + parent + DOB; within a round never fuzzy-merged
             (twins); unsure → "Who is …?" in the Inbox
   score     percentile within gender × age (pool widens until ≥ 25 children), composite
   flags     top / improved / push / declining / missing, each with evidence ids
                   │
         ti.queries (one read layer) ─► FastAPI ─► React PWA
                                                 └─ WebLLM worker for Ask (optional)
```

Persistent: users, schools ↔ coaches, rounds, uploads, records (raw rows), children registry,
coordinator decisions, events / races / picks / results / to-dos, settings, audit log.
Derived and rebuilt after every upload or decision: measurements, percentiles, flags, Inbox.

On the real HRS workbook (3,073 rows, 8 schools, run locally, never committed) the pipeline runs in
about 6 s and finds the repeated Shaikpet block (315 exact + 72 differing copies), the MRC
Filmnagar Class I → III paste, six placeholder groups (ball 2.5 m, shuttle 16 s), relay recorded in
levels/minutes at two schools and 111 dates of birth that do not fit the class. On the synthetic
demo (1,450 children, 3 rounds) linking is exact: 0 split, 0 merged, 6 rows sent to review.

## Tech choices (one line each)

- **FastAPI + SQLAlchemy** = one Python codebase for pipeline and API; SQLite locally, Postgres (Supabase) hosted by changing `TI_DATABASE_URL`.
- **openpyxl** = reads cell values *and* addresses, so every number cites `file › sheet › cell`.
- **rapidfuzz + jellyfish** = typo, initial (`K.Umesh`) and sound-alike name matching.
- **Rules for cleaning, checks, scores and flags** = the same files and decisions always give the same output; no model touches children's data.
- **React + Vite + Tailwind PWA** = installable on phones, works on laptops, offline shell; Apple-HIG styling (system font, 44 px targets, light/dark).
- **WebLLM (Qwen2.5-1.5B-Instruct q4, ~1 GB, JSON-schema constrained)** in a web worker = Ask runs on the device, free, offline after download. Lite (Qwen2.5-0.5B) for older phones, Best (Qwen3-1.7B). Fallback chain: browser model → laptop Ollama (`qwen2.5:3b`) → server rule parser.
- **JWT roles** = manager sees all schools, supervisor their schools, trainer their school.
- **Docker compose (app + Postgres 16)** = one image serves API and PWA; the same image runs on Render with managed Postgres (`Dockerfile`, `docker-compose.yml`, `render.yaml`).

## Design decisions

- **Pipeline (ETL) + rebuildable state**: ingest → clean → check → link → score → flag; a new upload or decision simply re-runs `rebuild()`.
- **Layered**: input, processing, store, one read layer (`ti.queries`), presentation. The PWA never sees raw files except through the receipt endpoint.
- **Provenance store**: every measurement keeps its record id and cell; the Receipt view shows the row as typed with neighbours, the round, upload date and file fingerprint.
- **Data problems ≠ children's problems**: suspect and disputed values are excluded from percentiles and shortlists until the coordinator decides; strong children held back by a check are listed, never dropped silently.
- **Human in the loop with undo**: Inbox decisions are stored as resolutions, survive re-runs, and can be undone.
- **AI where it is cheap and safe**: the model only maps a question to a validated query (`ti.ask.SCHEMA`); answers and shortlists are computed and cited. Retrieval is structured, not vector search.
- **Privacy by design**: the language model never receives names, DOBs or results; the real workbook is git-ignored. Hosting puts children's data in the programme's database, so real data needs HRS consent first.

## Meet selection

Each race has a discipline whose weights say which tests predict it (editable in `ti.shortlist`):
sprint = shuttle 70% + jump 30%, jumps = jump 80% + shuttle 20%, throws = ball 85% + jump 15%,
middle distance = relay 75% + shuttle 25%, relay = shuttle 60% + relay 40%, all-round = equal.
Age is counted on the meet date. A child's score is the weighted mean of their latest valid
percentiles; reasons show each value with its cell.

## Layout

| Path | What |
|---|---|
| `src/ti/template.py`, `ingest.py`, `clean.py` | HRS template mapping, workbook reader, cell cleaning |
| `src/ti/identity.py` | Name linking across rounds |
| `src/ti/pipeline.py` | Upload, checks, measurements, percentiles, flags, Inbox, decisions |
| `src/ti/shortlist.py`, `ask.py` | Meet shortlists; Ask schema, rule parser, executor |
| `src/ti/queries.py`, `api/` | Read layer and FastAPI routers (core, data, events, ask) |
| `src/ti/generator/`, `seed.py`, `verify.py` | Synthetic data on the template, demo seed, ground-truth check |
| `web/` | PWA: pages, components (Receipt, LineChart, Sheet…), WebLLM worker |
| `Dockerfile`, `docker-compose.yml`, `.env.example`, `.github/workflows/ci.yml` | Image, stack, settings, CI |
| `docs/superpowers/specs/2026-11-10-champion-v2-design.md` | v2 spec |

## Honest limits

- Round cadence and baseline norms are assumptions until HRS confirms them; percentiles are relative to this programme, not national norms.
- Percentiles are per round, so "improved" means improved relative to peers; raw progress (metres, seconds) is shown alongside.
- Relay endurance units differ between schools in the real data; those schools are kept out of relay comparisons until fixed.
- WebLLM needs WebGPU (recent Chrome/Edge, Android Chrome; Safari 26+); other browsers use rules.
- Planned: NLI check on explanations, multi-school name collisions across transfers, offline write queue.

Illustrations: unDraw (free licence), see `web/public/illus/SOURCES.md`.
