#!/usr/bin/env bash
# abstract: Start the local taxonomy layout tuning API server.
# out_of_scope: Production API serving, public ingress, and frontend build orchestration.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HOST="${TAXONOMY_LAYOUT_LAB_API_HOST:-127.0.0.1}"
PORT="${TAXONOMY_LAYOUT_LAB_API_PORT:-8765}"

cd "$ROOT_DIR/apps/api"
exec uv run python -m entrypoints.ops.taxonomy_layout_lab_server --host "$HOST" --port "$PORT"
