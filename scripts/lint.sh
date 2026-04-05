#!/usr/bin/env bash
# abstract: Run read-only lint validation for backend and frontend.
# out_of_scope: Type checking, test execution, and contract drift verification.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
API_DIR="$ROOT_DIR/apps/api"
CORPUS_DIR="$ROOT_DIR/apps/knowledge_corpus"

echo "[lint] backend (ruff)"
uv run --project "$API_DIR" ruff check "$API_DIR/src"

echo "[lint] backend (import-linter)"
uv run --project "$API_DIR" lint-imports --config "$API_DIR/pyproject.toml"

echo "[lint] knowledge corpus (ruff)"
uv run --project "$CORPUS_DIR" ruff check "$CORPUS_DIR/src" "$CORPUS_DIR/tests" "$CORPUS_DIR/alembic"

echo "[lint] js/ts (biome)"
pnpm run js:lint
