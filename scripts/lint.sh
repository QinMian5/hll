#!/usr/bin/env bash
# abstract: Run read-only lint validation for backend and frontend.
# out_of_scope: Type checking, test execution, and contract drift verification.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
API_DIR="$ROOT_DIR/apps/api"
WEB_DIR="$ROOT_DIR/apps/web"

echo "[lint] backend (ruff)"
uv run --project "$API_DIR" ruff check "$API_DIR/src"

echo "[lint] frontend (biome)"
pnpm --dir "$WEB_DIR" run ci
