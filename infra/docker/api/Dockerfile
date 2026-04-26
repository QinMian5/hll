# abstract: Build and runtime image for the FastAPI service and migration runner.
# out_of_scope: Compose orchestration policy and PostgreSQL extension packaging.
FROM ghcr.io/astral-sh/uv:0.10.3-python3.14-trixie-slim

WORKDIR /app

COPY pyproject.toml /app/pyproject.toml
COPY uv.lock /app/uv.lock
COPY packages/job_queue_integration/pyproject.toml /app/packages/job_queue_integration/pyproject.toml
COPY packages/job_queue_integration/src /app/packages/job_queue_integration/src
COPY apps/api/pyproject.toml /app/apps/api/pyproject.toml
COPY apps/api/src /app/apps/api/src
COPY apps/api/alembic.ini /app/apps/api/alembic.ini
COPY apps/api/alembic /app/apps/api/alembic
COPY infra/docker/api/run-api.sh /app/bin/
COPY infra/docker/api/run-worker.sh /app/bin/
COPY infra/docker/api/run-taxonomy-classification-runtime.sh /app/bin/
COPY infra/docker/api/run-taxonomy-classification-webhook-receiver.sh /app/bin/

RUN chmod +x /app/bin/run-api.sh /app/bin/run-worker.sh /app/bin/run-taxonomy-classification-runtime.sh /app/bin/run-taxonomy-classification-webhook-receiver.sh && uv sync --frozen --package api --group dev

ENV PATH="/app/.venv/bin:${PATH}"

EXPOSE 8000

CMD ["/app/bin/run-api.sh"]
