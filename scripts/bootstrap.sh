#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
API_DIR="$ROOT_DIR/apps/api"

uv --directory "$API_DIR" sync

(
  cd "$ROOT_DIR"
  pnpm install
)

echo "bootstrap complete"
