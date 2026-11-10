#!/usr/bin/env sh
# One command for the local demo: seed the synthetic workspace if needed, then run API + web.
#   ./dev.sh            API on :8000, web on :5173 (open http://localhost:5173)
#   ./dev.sh --fresh    rebuild the demo store from the synthetic workbooks first
set -e
cd "$(dirname "$0")"
uv sync -q
[ -d web/node_modules ] || (cd web && npm install --no-audit --no-fund)
if [ "$1" = "--fresh" ] || [ ! -f var/ti.db ]; then uv run python -m ti.seed --fresh; fi
# Laptop model for Ask: start Ollama (allowing the browser to call it) if it is installed and idle.
if command -v ollama >/dev/null && ! curl -sf localhost:11434/api/tags >/dev/null; then
  OLLAMA_ORIGINS="*" ollama serve >/dev/null 2>&1 &
fi
export TI_SECRET="${TI_SECRET:-local-demo-secret-please-change-0123456789}"
uv run uvicorn ti.api:app --port 8000 &
API=$!
trap 'kill $API 2>/dev/null' EXIT INT TERM
cd web && npx vite --port 5173 --host
