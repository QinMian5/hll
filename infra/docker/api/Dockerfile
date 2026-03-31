# abstract: Build and runtime image for the FastAPI service and migration runner.
# out_of_scope: Compose orchestration policy and PostgreSQL extension packaging.
FROM ghcr.io/astral-sh/uv:python3.14-bookworm-slim

WORKDIR /app

COPY apps/api/pyproject.toml /app/pyproject.toml
COPY apps/api/uv.lock /app/uv.lock
COPY apps/api/README.md /app/README.md
COPY apps/api/src /app/src
COPY alembic.ini /app/alembic.ini
COPY alembic /app/alembic

RUN uv sync --frozen --no-dev

ENV PATH="/app/.venv/bin:${PATH}"

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "main:app", "--app-dir", "src", "--host", "0.0.0.0", "--port", "8000"]

