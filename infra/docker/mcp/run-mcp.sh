#!/usr/bin/env sh
# abstract: Stable MCP service startup wrapper for uvicorn process launch.
# out_of_scope: Logto provisioning and compose dependency orchestration.

set -eu

if [ "${MCP_RELOAD:-0}" = "1" ]; then
  exec uvicorn knowledge_mcp.http_app:create_app --factory --app-dir apps/mcp/src --host "${KNOWLEDGE_MCP_HOST:-0.0.0.0}" --port "${KNOWLEDGE_MCP_PORT:-8080}" --reload
fi

exec uvicorn knowledge_mcp.http_app:create_app --factory --app-dir apps/mcp/src --host "${KNOWLEDGE_MCP_HOST:-0.0.0.0}" --port "${KNOWLEDGE_MCP_PORT:-8080}"
