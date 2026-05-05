#!/usr/bin/env bash
# abstract: Precompute taxonomy card-scope layouts through the API operator runtime.
# out_of_scope: Public API serving, scheduling, and alternate layout persistence.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

cd "$ROOT_DIR/apps/api"
exec uv run python -m entrypoints.ops.taxonomy_layout_precompute "$@"
