#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WEB_DIR="$ROOT_DIR/apps/web"

if [[ ! -d "$WEB_DIR" ]]; then
  WEB_DIR="$ROOT_DIR/frontend"
fi

if [[ ! -f "$WEB_DIR/package.json" ]]; then
  echo "missing frontend project at $WEB_DIR" >&2
  exit 1
fi

cd "$WEB_DIR"
pnpm run dev
