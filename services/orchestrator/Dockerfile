# Build context is the repo root so the libs/ path dependencies resolve inside
# the image.
FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:0.11 /uv /usr/local/bin/uv

# The venv lives outside /app/services so the dev-mode bind mount of ./services
# cannot hide it.
ENV UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONUNBUFFERED=1

COPY libs/harness_auth /app/libs/harness_auth
COPY libs/harness_models /app/libs/harness_models

WORKDIR /app/services/orchestrator
COPY services/orchestrator/pyproject.toml services/orchestrator/uv.lock ./
RUN uv sync --frozen
COPY services/orchestrator/ ./

EXPOSE 8010
# harness_auth and harness_models are installed editable, so --reload-dir covers them too.
CMD ["/opt/venv/bin/uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8010", \
     "--reload", "--reload-dir", "/app/services/orchestrator", "--reload-dir", "/app/libs"]
