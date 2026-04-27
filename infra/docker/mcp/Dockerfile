# abstract: Build and runtime image for the public MCP service.
# out_of_scope: Compose orchestration policy, Logto provisioning, and migration execution.
FROM ghcr.io/astral-sh/uv:0.10.3-python3.14-trixie-slim

WORKDIR /workspace/mianqin/Code/knowledge

COPY pyproject.toml /workspace/mianqin/Code/knowledge/pyproject.toml
COPY uv.lock /workspace/mianqin/Code/knowledge/uv.lock
COPY --from=job_queue_mcp_python_client pyproject.toml /workspace/mianqin/Code/job-queue-mcp/packages/python-client/pyproject.toml
COPY --from=job_queue_mcp_python_client README.md /workspace/mianqin/Code/job-queue-mcp/packages/python-client/README.md
COPY --from=job_queue_mcp_python_client src /workspace/mianqin/Code/job-queue-mcp/packages/python-client/src
COPY apps/api/pyproject.toml /workspace/mianqin/Code/knowledge/apps/api/pyproject.toml
COPY apps/cli/pyproject.toml /workspace/mianqin/Code/knowledge/apps/cli/pyproject.toml
COPY apps/knowledge_corpus/pyproject.toml /workspace/mianqin/Code/knowledge/apps/knowledge_corpus/pyproject.toml
COPY apps/mcp/pyproject.toml /workspace/mianqin/Code/knowledge/apps/mcp/pyproject.toml
COPY apps/source_pipeline/pyproject.toml /workspace/mianqin/Code/knowledge/apps/source_pipeline/pyproject.toml
COPY packages/contracts/generated/python/pyproject.toml /workspace/mianqin/Code/knowledge/packages/contracts/generated/python/pyproject.toml
COPY packages/contracts/generated/python/src /workspace/mianqin/Code/knowledge/packages/contracts/generated/python/src
COPY apps/mcp/alembic.ini /workspace/mianqin/Code/knowledge/apps/mcp/alembic.ini
COPY apps/mcp/alembic /workspace/mianqin/Code/knowledge/apps/mcp/alembic
COPY apps/mcp/src /workspace/mianqin/Code/knowledge/apps/mcp/src
COPY infra/docker/mcp/run-mcp.sh /workspace/mianqin/Code/knowledge/bin/

RUN ln -s /workspace/mianqin/Code/knowledge /app && chmod +x /app/bin/run-mcp.sh && uv sync --frozen --package knowledge-mcp --group dev

ENV PATH="/app/.venv/bin:${PATH}"

EXPOSE 8080

CMD ["/app/bin/run-mcp.sh"]
