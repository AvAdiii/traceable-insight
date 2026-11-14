# GitHub issues: Hackathon 2

Labels: `B1 Data`, `B2 API`, `B3 Web`, `B4 Deploy` (one per box in the architecture diagram).
Milestone: `Hackathon 2`. Every title starts with its tag. Each issue is closed by one pull
request from its owner, squash-merged into `main`. The CI pull request goes first so every later
change is checked; the store (#4) lands before the pipeline (#2) because the pipeline writes to it.

Merge order: #10 → #1 → #4 → #2 → #3 → #5 → #6 → #7 → #8 → #9 → #11 → #12

| # | Title | Label | Owner | Done when |
|---|---|---|---|---|
| 1 | [B1] HRS template reader and cell cleaning with citations | B1 Data | A V Aditya | template sheets found by header; every value keeps file › sheet › cell; typos repaired and explained (`tests/test_clean.py`) |
| 2 | [B1] Identity across rounds, data checks, percentiles and flags | B1 Data | A V Aditya | children linked by name, initials, parent, DOB; checks raise Inbox issues; percentiles within gender × age; stackable flags |
| 3 | [B1] Synthetic demo workbooks, seed and ground-truth check | B1 Data | A V Aditya | three rounds of synthetic workbooks with planted problems; linking exact against `ground_truth.json` (`tests/test_pipeline_v2.py`) |
| 4 | [B2] Postgres-ready store, JWT roles and settings | B2 API | Shriya Kansal | same SQLAlchemy models on SQLite and Postgres via `TI_DATABASE_URL`; manager / supervisor / trainer tokens |
| 5 | [B2] Read layer, uploads, Inbox decisions and cell receipts | B2 API | Shriya Kansal | one read layer; upload refuses duplicates; decisions with undo; receipt shows the row as typed |
| 6 | [B2] Meets, AI shortlist with reasons, Ask executor | B2 API | Shriya Kansal | races, picks, reserves, results, to-dos; every shortlist reason cites a cell; Ask runs validated specs; demo seed (`tests/test_ask_api.py`) |
| 7 | [B3] PWA shell, API client, auth and shared components | B3 Web | Tanishi Tyagi | installable PWA, sign-in, tab bar, Receipt sheet; Streamlit view retired |
| 8 | [B3] Screens: Home, Children, Child, Schools, Calendar, Event, Inbox, Upload, Settings | B3 Web | Tanishi Tyagi | every screen on phone and laptop, light and dark; every number opens its receipt |
| 9 | [B3] On-device Ask with WebLLM and fallback chain | B3 Web | Tanishi Tyagi | browser model → laptop Ollama → server rules; model choice in Settings |
| 10 | [B4] Hack 2 issues and CI for tests, web build and image | B4 Deploy | Chandrani Saha | labels, milestone and these issues on GitHub; CI green on every PR |
| 11 | [B4] Docker compose stack with Postgres, healthcheck and first-run seed | B4 Deploy | Chandrani Saha | fresh clone → `docker compose up --build` → app at :8000 with demo logins; data survives a restart |
| 12 | [B4] README and docs for v2, Docker and the hosted demo | B4 Deploy | Chandrani Saha | README covers Docker, configuration, demo logins, architecture, hosted link |
