#!/usr/bin/env bash
# abstract: Run the default fail-fast quality gate chain for local and CI usage.
# out_of_scope: Auto-fix operations, deployment smoke checks, and migration orchestration.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "[check] lint"
bash "$ROOT_DIR/scripts/lint.sh"

echo "[check] typecheck"
bash "$ROOT_DIR/scripts/typecheck.sh"

echo "[check] test"
bash "$ROOT_DIR/scripts/run-tests.sh"

echo "[check] contract drift"
bash "$ROOT_DIR/scripts/contracts-check.sh"
