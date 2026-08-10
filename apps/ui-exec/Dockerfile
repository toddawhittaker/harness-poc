# Build context is the repo root, matching every other image here.
FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:0.11 /uv /usr/local/bin/uv

# The venv lives outside /app/apps so the dev-mode bind mount cannot hide it.
ENV UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONUNBUFFERED=1

# The workspace root: one lockfile covers every member (see pyproject.toml).
COPY pyproject.toml uv.lock /app/

WORKDIR /app/apps/ui-exec
COPY apps/ui-exec/pyproject.toml ./
RUN uv sync --frozen
COPY apps/ui-exec/ ./

EXPOSE 8081
# -w is chainlit's watcher, the surface equivalent of uvicorn --reload.
CMD ["/opt/venv/bin/chainlit", "run", "app.py", "-w", "--host", "0.0.0.0", "--port", "8081"]
