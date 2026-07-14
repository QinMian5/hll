#!/usr/bin/env bash
# abstract: Export the production API knowledge graph and taxonomy data snapshot.
# out_of_scope: Development database mutation and migration execution.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
API_DIR="$ROOT_DIR/apps/api"
UV_CACHE_DIR="$ROOT_DIR/.uv-cache"
COMPOSE_BASE="$ROOT_DIR/infra/compose/docker-compose.base.yml"
COMPOSE_PROD="$ROOT_DIR/infra/compose/docker-compose.prod.yml"
SNAPSHOT_PATH="${1:-$ROOT_DIR/apps/api/bootstrap/prod-api-bootstrap.sql}"
SNAPSHOT_DIR="$(dirname "$SNAPSHOT_PATH")"
TMP_PATH="$SNAPSHOT_PATH.tmp"

compose_args=(
  -f "$COMPOSE_BASE"
  -f "$COMPOSE_PROD"
)

table_args_output="$(
  UV_CACHE_DIR="$UV_CACHE_DIR" uv --directory "$API_DIR" run python -m entrypoints.ops.prod_snapshot_bootstrap dump-table-args
)"
if [[ -z "$table_args_output" ]]; then
  echo "error: no bootstrap tables were resolved" >&2
  exit 1
fi
mapfile -t table_args <<<"$table_args_output"

mkdir -p "$SNAPSHOT_DIR"

{
  printf '%s\n' '-- abstract: Generated production API data snapshot for development bootstrap.'
  printf '%s\n' '-- out_of_scope: Schema migrations, role provisioning, and production database mutation.'
  printf '%s\n' '-- generated_by: scripts/export-prod-api-bootstrap-snapshot.sh'
  docker compose "${compose_args[@]}" exec -T postgres sh -lc \
    'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --data-only --column-inserts --disable-triggers --no-owner --no-privileges "$@"' \
    sh "${table_args[@]}"
} >"$TMP_PATH"

mv "$TMP_PATH" "$SNAPSHOT_PATH"
echo "snapshot_path=$SNAPSHOT_PATH"
