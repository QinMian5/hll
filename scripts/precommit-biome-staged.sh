#!/usr/bin/env bash
# abstract: Apply fast Biome fixes to staged frontend files before commit.
# out_of_scope: Backend quality gates, full test execution, and CI-only checks.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WEB_DIR="$ROOT_DIR/apps/web"

echo "[pre-commit] frontend staged fix (biome)"
pnpm --dir "$WEB_DIR" exec biome check --staged --write
