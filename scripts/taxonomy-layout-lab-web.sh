#!/usr/bin/env bash
# abstract: Start the standalone taxonomy layout tuning web page.
# out_of_scope: Production web server startup, API server startup, and browser automation.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HOST="${TAXONOMY_LAYOUT_LAB_WEB_HOST:-127.0.0.1}"
PORT="${TAXONOMY_LAYOUT_LAB_WEB_PORT:-5175}"

cd "$ROOT_DIR/apps/web"
exec pnpm exec vite --host "$HOST" --port "$PORT"
