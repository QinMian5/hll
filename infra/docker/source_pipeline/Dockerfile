# abstract: Build and runtime image for the source-pipeline orchestrator and migration runner.
# out_of_scope: Compose orchestration policy and PostgreSQL server packaging.
FROM ghcr.io/astral-sh/uv:0.10.3-python3.14-trixie-slim

WORKDIR /app

COPY pyproject.toml /app/pyproject.toml
COPY uv.lock /app/uv.lock
COPY packages/job_queue_integration/pyproject.toml /app/packages/job_queue_integration/pyproject.toml
COPY packages/job_queue_integration/src /app/packages/job_queue_integration/src
COPY apps/source_pipeline/pyproject.toml /app/apps/source_pipeline/pyproject.toml
COPY apps/source_pipeline/src /app/apps/source_pipeline/src
COPY apps/source_pipeline/alembic.ini /app/apps/source_pipeline/alembic.ini
COPY apps/source_pipeline/alembic /app/apps/source_pipeline/alembic
COPY infra/docker/source_pipeline/run-orchestrator.sh /app/bin/
COPY infra/docker/source_pipeline/run-webhook-receiver.sh /app/bin/

RUN chmod +x /app/bin/run-orchestrator.sh /app/bin/run-webhook-receiver.sh && uv sync --frozen --package source-pipeline --group dev

ENV PATH="/app/.venv/bin:${PATH}"

CMD ["/app/bin/run-orchestrator.sh"]
