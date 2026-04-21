#!/usr/bin/env bash
# abstract: Run read-only type checks for backend and frontend.
# out_of_scope: Lint auto-fix, test execution, and contract drift verification.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
API_DIR="$ROOT_DIR/apps/api"
CORPUS_DIR="$ROOT_DIR/apps/knowledge_corpus"
SOURCE_PIPELINE_DIR="$ROOT_DIR/apps/source_pipeline"

echo "[typecheck] backend (ty)"
uv run --project "$API_DIR" ty check --project "$API_DIR" "$API_DIR/src"

echo "[typecheck] knowledge corpus (ty)"
uv run --project "$CORPUS_DIR" ty check --project "$CORPUS_DIR" "$CORPUS_DIR/src"

echo "[typecheck] source pipeline (ty)"
uv run --project "$SOURCE_PIPELINE_DIR" ty check --project "$SOURCE_PIPELINE_DIR" "$SOURCE_PIPELINE_DIR/src"

echo "[typecheck] js/ts (tsc)"
pnpm run js:typecheck
