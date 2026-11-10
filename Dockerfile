# Hosted build: one container serves the API and the built PWA.
FROM node:22-slim AS web
WORKDIR /web
COPY web/package*.json ./
RUN npm ci --no-audit --no-fund
COPY web/ ./
RUN npx vite build

FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir uv
COPY pyproject.toml uv.lock README.md ./
COPY src ./src
RUN uv sync --frozen --no-dev --extra hosted
COPY --from=web /web/dist ./web/dist
COPY data/demo ./data/demo
ENV TI_UPLOADS=/data/uploads PORT=8000
EXPOSE 8000
CMD ["sh", "-c", "uv run --no-dev python -m ti.seed && uv run --no-dev uvicorn ti.api:app --host 0.0.0.0 --port ${PORT}"]
