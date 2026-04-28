#!/usr/bin/env sh
# abstract: Stable MCP service startup wrapper for uvicorn process launch.
# out_of_scope: Logto provisioning and compose dependency orchestration.

set -eu

: "${KNOWLEDGE_MCP_HOST:?KNOWLEDGE_MCP_HOST is required}"
: "${KNOWLEDGE_MCP_PORT:?KNOWLEDGE_MCP_PORT is required}"

if [ "${MCP_RELOAD:-0}" = "1" ]; then
  exec uvicorn knowledge_mcp.http_app:create_app --factory --app-dir apps/mcp/src --host "$KNOWLEDGE_MCP_HOST" --port "$KNOWLEDGE_MCP_PORT" --reload
fi

exec uvicorn knowledge_mcp.http_app:create_app --factory --app-dir apps/mcp/src --host "$KNOWLEDGE_MCP_HOST" --port "$KNOWLEDGE_MCP_PORT"
