#!/usr/bin/env bash
# abstract: Run the default test gate for backend unit tests and frontend vitest checks.
# out_of_scope: Integration tests, contract verification, and lint/type checking.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
API_DIR="$ROOT_DIR/apps/api"
CORPUS_DIR="$ROOT_DIR/apps/knowledge_corpus"
SOURCE_PIPELINE_DIR="$ROOT_DIR/apps/source_pipeline"
WEB_DIR="$ROOT_DIR/apps/web"

echo "[test] backend unit (pytest)"
uv --directory "$API_DIR" run pytest "$API_DIR/tests/unit"

echo "[test] knowledge corpus unit (pytest)"
uv --directory "$CORPUS_DIR" run pytest "$CORPUS_DIR/tests/unit"

echo "[test] source pipeline unit (pytest)"
uv --directory "$SOURCE_PIPELINE_DIR" run pytest "$SOURCE_PIPELINE_DIR/tests/unit"

echo "[test] frontend (vitest)"
pnpm run web:test
