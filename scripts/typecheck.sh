#!/usr/bin/env bash
# abstract: Run read-only type checks for backend and frontend.
# out_of_scope: Lint auto-fix, test execution, and contract drift verification.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
API_DIR="$ROOT_DIR/apps/api"
WEB_DIR="$ROOT_DIR/apps/web"

echo "[typecheck] backend (ty)"
uv run --project "$API_DIR" ty check --project "$API_DIR" "$API_DIR/src"

echo "[typecheck] frontend (tsc)"
pnpm --dir "$WEB_DIR" run typecheck
