# abstract: Build and runtime image for the source-pipeline orchestrator and migration runner.
# out_of_scope: Compose orchestration policy and PostgreSQL server packaging.
FROM ghcr.io/astral-sh/uv:0.10.3-python3.14-trixie-slim

WORKDIR /workspace/mianqin/Code/knowledge

COPY pyproject.toml /workspace/mianqin/Code/knowledge/pyproject.toml
COPY uv.lock /workspace/mianqin/Code/knowledge/uv.lock
COPY --from=job_queue_mcp_python_client pyproject.toml /workspace/job-queue-mcp/packages/python-client/pyproject.toml
COPY --from=job_queue_mcp_python_client README.md /workspace/job-queue-mcp/packages/python-client/README.md
COPY --from=job_queue_mcp_python_client src /workspace/job-queue-mcp/packages/python-client/src
COPY apps/source_pipeline/pyproject.toml /workspace/mianqin/Code/knowledge/apps/source_pipeline/pyproject.toml
COPY apps/source_pipeline/src /workspace/mianqin/Code/knowledge/apps/source_pipeline/src
COPY apps/source_pipeline/alembic.ini /workspace/mianqin/Code/knowledge/apps/source_pipeline/alembic.ini
COPY apps/source_pipeline/alembic /workspace/mianqin/Code/knowledge/apps/source_pipeline/alembic
COPY infra/docker/source_pipeline/run-orchestrator.sh /workspace/mianqin/Code/knowledge/bin/
COPY infra/docker/source_pipeline/run-webhook-receiver.sh /workspace/mianqin/Code/knowledge/bin/

RUN ln -s /workspace/mianqin/Code/knowledge /app && chmod +x /app/bin/run-orchestrator.sh /app/bin/run-webhook-receiver.sh && uv sync --frozen --package source-pipeline --group dev

ENV PATH="/app/.venv/bin:${PATH}"

CMD ["/app/bin/run-orchestrator.sh"]
