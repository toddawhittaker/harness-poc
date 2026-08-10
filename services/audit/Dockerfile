# Build context is the repo root (see docker-compose.yml).
FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:0.11 /uv /usr/local/bin/uv

# The venv lives outside /app/services so the dev-mode bind mount of ./services
# cannot hide it.
ENV UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONUNBUFFERED=1

# The workspace root: one lockfile covers every member (see pyproject.toml).
COPY pyproject.toml uv.lock /app/

WORKDIR /app/services/audit
COPY services/audit/pyproject.toml ./
RUN uv sync --frozen
COPY services/audit/ ./

EXPOSE 8030
CMD ["/opt/venv/bin/uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8030", "--reload"]
