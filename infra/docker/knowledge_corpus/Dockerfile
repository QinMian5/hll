#
# abstract: Build image for knowledge corpus Alembic migrations and local schema tooling.
# out_of_scope: Docker Compose orchestration and PostgreSQL server packaging.
FROM ghcr.io/astral-sh/uv:0.10.3-python3.14-trixie-slim

WORKDIR /app

COPY pyproject.toml /app/pyproject.toml
COPY uv.lock /app/uv.lock
COPY apps/knowledge_corpus/pyproject.toml /app/apps/knowledge_corpus/pyproject.toml
COPY apps/knowledge_corpus/src /app/apps/knowledge_corpus/src
COPY apps/knowledge_corpus/alembic.ini /app/apps/knowledge_corpus/alembic.ini
COPY apps/knowledge_corpus/alembic /app/apps/knowledge_corpus/alembic

RUN uv sync --frozen --no-dev --package knowledge-corpus

ENV PATH="/app/.venv/bin:${PATH}"

CMD ["alembic", "-c", "/app/apps/knowledge_corpus/alembic.ini", "upgrade", "head"]
