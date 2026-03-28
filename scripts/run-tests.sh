#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
API_DIR="$ROOT_DIR/apps/api"
WEB_DIR="$ROOT_DIR/apps/web"

if [[ ! -d "$API_DIR" ]]; then
  API_DIR="$ROOT_DIR/backend"
fi
if [[ ! -d "$WEB_DIR" ]]; then
  WEB_DIR="$ROOT_DIR/frontend"
fi

if [[ -f "$API_DIR/pyproject.toml" ]]; then
  (
    cd "$API_DIR"
    uv run pytest
  )
fi

if [[ -f "$WEB_DIR/package.json" ]]; then
  (
    cd "$WEB_DIR"
    pnpm run test -- --run
  )
fi
