# Build context is the repo root so the libs/harness_auth path dependency
# resolves inside the image.
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

# The workspace root: one lockfile covers every member (see pyproject.toml).
COPY pyproject.toml uv.lock /app/

WORKDIR /app/services/gateway
COPY services/gateway/pyproject.toml ./
RUN uv sync --frozen
COPY services/gateway/ ./

EXPOSE 8000
# harness_auth is installed editable, so --reload-dir covers it too.
CMD ["/opt/venv/bin/uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000", \
     "--reload", "--reload-dir", "/app/services/gateway", "--reload-dir", "/app/libs"]
