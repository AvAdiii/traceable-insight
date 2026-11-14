# Stride: one image serves the API and the built PWA.
#   docker compose up --build        app + Postgres (see docker-compose.yml)
#   docker build -t stride . && docker run -p 8000:8000 stride    SQLite inside the container

# --- 1. Build the phone app (PWA) -------------------------------------------------------------
FROM node:22-slim AS web
WORKDIR /web
COPY web/package.json web/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY web/ ./
RUN npx vite build

# --- 2. Python dependencies into a virtualenv -------------------------------------------------
FROM python:3.12-slim AS deps
COPY --from=ghcr.io/astral-sh/uv:0.8 /uv /usr/local/bin/uv
ENV UV_LINK_MODE=copy UV_COMPILE_BYTECODE=1 UV_PYTHON_DOWNLOADS=never
WORKDIR /app
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --extra hosted --no-install-project
COPY src ./src
RUN uv sync --frozen --no-dev --extra hosted --no-editable

# --- 3. Runtime: no build tools, non-root user ------------------------------------------------
FROM python:3.12-slim
RUN useradd --create-home --uid 1000 stride \
    && mkdir -p /data/uploads /data/var \
    && chown -R stride:stride /data
WORKDIR /app
COPY --from=deps /app/.venv /app/.venv
COPY --from=web /web/dist ./web/dist
COPY data/demo ./data/demo
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    TI_ROOT=/app \
    TI_VAR=/data/var \
    TI_UPLOADS=/data/uploads \
    TI_CORS="" \
    PORT=8000
USER stride
EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=5s --start-period=60s --retries=5 \
    CMD python -c "import os,urllib.request; urllib.request.urlopen(f'http://127.0.0.1:{os.environ.get(\"PORT\",\"8000\")}/api/health', timeout=4)"
# First run seeds the synthetic demo; later runs see existing users and skip, so data survives.
CMD ["sh", "-c", "python -m ti.seed && exec uvicorn ti.api:app --host 0.0.0.0 --port ${PORT} --proxy-headers"]
