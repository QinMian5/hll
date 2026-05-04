#!/usr/bin/env bash
# abstract: Run read-only type checks for backend and frontend.
# out_of_scope: Lint auto-fix, test execution, and contract drift verification.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
API_DIR="$ROOT_DIR/apps/api"
CORPUS_DIR="$ROOT_DIR/apps/knowledge_corpus"
MCP_DIR="$ROOT_DIR/apps/mcp"
OPERATOR_TOOLS_DIR="$ROOT_DIR/apps/operator_tools"
SOURCE_PIPELINE_DIR="$ROOT_DIR/apps/source_pipeline"

cd "$ROOT_DIR"

echo "[typecheck] backend (ty)"
uv run --project "$API_DIR" ty check --project "$API_DIR" apps/api/src

echo "[typecheck] knowledge corpus (ty)"
uv run --project "$CORPUS_DIR" ty check --project "$CORPUS_DIR" apps/knowledge_corpus/src

echo "[typecheck] mcp (ty)"
uv run --project "$MCP_DIR" ty check --project "$MCP_DIR" apps/mcp/src

echo "[typecheck] operator tools (ty)"
uv run --project "$OPERATOR_TOOLS_DIR" ty check --project "$OPERATOR_TOOLS_DIR" apps/operator_tools/src

echo "[typecheck] source pipeline (ty)"
uv run --project "$SOURCE_PIPELINE_DIR" ty check --project "$SOURCE_PIPELINE_DIR" apps/source_pipeline/src

echo "[typecheck] js/ts (tsc)"
pnpm run js:typecheck
