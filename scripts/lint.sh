#!/usr/bin/env bash
# abstract: Run read-only lint validation for backend and frontend.
# out_of_scope: Type checking, test execution, and contract drift verification.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
API_DIR="$ROOT_DIR/apps/api"
CORPUS_DIR="$ROOT_DIR/apps/knowledge_corpus"
MCP_DIR="$ROOT_DIR/apps/mcp"
SOURCE_PIPELINE_DIR="$ROOT_DIR/apps/source_pipeline"

cd "$ROOT_DIR"

echo "[lint] backend (ruff)"
uv run --project "$API_DIR" ruff check apps/api/src

echo "[lint] backend (import-linter)"
uv run --project "$API_DIR" lint-imports --config pyproject.toml

echo "[lint] knowledge corpus (ruff)"
uv run --project "$CORPUS_DIR" ruff check \
  apps/knowledge_corpus/src \
  apps/knowledge_corpus/tests \
  apps/knowledge_corpus/alembic

echo "[lint] mcp (ruff)"
uv run --project "$MCP_DIR" ruff check apps/mcp/src apps/mcp/tests apps/mcp/alembic

echo "[lint] source pipeline (ruff)"
uv run --project "$SOURCE_PIPELINE_DIR" ruff check \
  apps/source_pipeline/src \
  apps/source_pipeline/tests \
  apps/source_pipeline/alembic

echo "[lint] js/ts (biome)"
pnpm run js:lint
