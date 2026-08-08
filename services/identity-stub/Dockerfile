# Build context is the repo root (see docker-compose.yml) so that services
# needing libs/harness_auth can copy it. This one does not.
FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:0.11 /uv /usr/local/bin/uv

# The venv lives outside /app/services so the dev-mode bind mount of ./services
# cannot hide it.
ENV UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONUNBUFFERED=1

WORKDIR /app/services/identity-stub
COPY services/identity-stub/pyproject.toml services/identity-stub/uv.lock ./
RUN uv sync --frozen
COPY services/identity-stub/ ./

EXPOSE 8001
CMD ["/opt/venv/bin/uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8001", "--reload"]
