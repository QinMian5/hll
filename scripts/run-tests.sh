#!/usr/bin/env bash
# abstract: Run the default test gate for backend unit tests and frontend vitest checks.
# out_of_scope: Integration tests, contract verification, and lint/type checking.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
API_DIR="$ROOT_DIR/apps/api"
WEB_DIR="$ROOT_DIR/apps/web"

echo "[test] backend unit (pytest)"
uv --directory "$API_DIR" run pytest "$API_DIR/tests/unit"

echo "[test] frontend (vitest)"
pnpm run web:test
