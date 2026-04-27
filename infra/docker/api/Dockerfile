# abstract: Build and runtime image for the FastAPI service and migration runner.
# out_of_scope: Compose orchestration policy and PostgreSQL extension packaging.
FROM ghcr.io/astral-sh/uv:0.10.3-python3.14-trixie-slim

WORKDIR /workspace/mianqin/Code/knowledge

COPY pyproject.toml /workspace/mianqin/Code/knowledge/pyproject.toml
COPY uv.lock /workspace/mianqin/Code/knowledge/uv.lock
COPY --from=job_queue_mcp_python_client pyproject.toml /workspace/job-queue-mcp/packages/python-client/pyproject.toml
COPY --from=job_queue_mcp_python_client README.md /workspace/job-queue-mcp/packages/python-client/README.md
COPY --from=job_queue_mcp_python_client src /workspace/job-queue-mcp/packages/python-client/src
COPY apps/api/pyproject.toml /workspace/mianqin/Code/knowledge/apps/api/pyproject.toml
COPY apps/api/src /workspace/mianqin/Code/knowledge/apps/api/src
COPY apps/api/alembic.ini /workspace/mianqin/Code/knowledge/apps/api/alembic.ini
COPY apps/api/alembic /workspace/mianqin/Code/knowledge/apps/api/alembic
COPY infra/docker/api/run-api.sh /workspace/mianqin/Code/knowledge/bin/
COPY infra/docker/api/run-worker.sh /workspace/mianqin/Code/knowledge/bin/
COPY infra/docker/api/run-taxonomy-classification-runtime.sh /workspace/mianqin/Code/knowledge/bin/
COPY infra/docker/api/run-taxonomy-classification-webhook-receiver.sh /workspace/mianqin/Code/knowledge/bin/

RUN ln -s /workspace/mianqin/Code/knowledge /app && chmod +x /app/bin/run-api.sh /app/bin/run-worker.sh /app/bin/run-taxonomy-classification-runtime.sh /app/bin/run-taxonomy-classification-webhook-receiver.sh && uv sync --frozen --package api --group dev

ENV PATH="/app/.venv/bin:${PATH}"

EXPOSE 8000

CMD ["/app/bin/run-api.sh"]
