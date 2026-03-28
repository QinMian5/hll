#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
API_DIR="$ROOT_DIR/apps/api"

if [[ ! -d "$API_DIR" ]]; then
  API_DIR="$ROOT_DIR/backend"
fi

if [[ ! -f "$API_DIR/pyproject.toml" ]]; then
  echo "missing backend project at $API_DIR" >&2
  exit 1
fi

cd "$API_DIR"
uv run uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
