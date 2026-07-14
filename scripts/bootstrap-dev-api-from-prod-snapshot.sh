#!/usr/bin/env bash
# abstract: Reset the development API database and restore the production snapshot.
# out_of_scope: Production database mutation and production snapshot generation.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
API_DIR="$ROOT_DIR/apps/api"
UV_CACHE_DIR="$ROOT_DIR/.uv-cache"
COMPOSE_BASE="$ROOT_DIR/infra/compose/docker-compose.base.yml"
COMPOSE_ENV="$ROOT_DIR/infra/env/.env.dev"
COMPOSE_DEV="$ROOT_DIR/infra/compose/docker-compose.dev.yml"
SNAPSHOT_PATH="${1:-$ROOT_DIR/apps/api/bootstrap/prod-api-bootstrap.sql}"

source "$ROOT_DIR/scripts/lib/postgres-role-bootstrap.sh"
source "$ROOT_DIR/scripts/lib/runtime-env.sh"

if [[ ! -f "$SNAPSHOT_PATH" ]]; then
  echo "error: snapshot file does not exist: $SNAPSHOT_PATH" >&2
  echo "hint: run scripts/export-prod-api-bootstrap-snapshot.sh first" >&2
  exit 1
fi

UV_CACHE_DIR="$UV_CACHE_DIR" uv --directory "$API_DIR" run python -m entrypoints.ops.prod_snapshot_bootstrap \
  validate-dev-env "$COMPOSE_ENV"

truncate_sql="$(
  UV_CACHE_DIR="$UV_CACHE_DIR" uv --directory "$API_DIR" run python -m entrypoints.ops.prod_snapshot_bootstrap truncate-sql
)"

compose_args=(
  -f "$COMPOSE_BASE"
  -f "$COMPOSE_DEV"
)

materialize_runtime_env dev "$COMPOSE_ENV"
converge_online_postgres_roles "${compose_args[@]}"
docker compose "${compose_args[@]}" rm -f migrate >/dev/null 2>&1 || true
docker compose "${compose_args[@]}" run --rm migrate

docker compose "${compose_args[@]}" stop \
  api \
  worker \
  taxonomy_view_layout_runtime \
  taxonomy_classification_runtime \
  taxonomy_classification_webhook_receiver >/dev/null 2>&1 || true

{
  printf '%s\n' "$truncate_sql"
  cat "$SNAPSHOT_PATH"
} | docker compose "${compose_args[@]}" exec -T postgres sh -lc \
  'psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"'

docker compose "${compose_args[@]}" up -d --wait redis
docker compose "${compose_args[@]}" exec -T redis redis-cli FLUSHDB >/dev/null

docker compose "${compose_args[@]}" exec -T postgres sh -lc \
  'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atc "select '\''nodes'\'', count(*) from nodes union all select '\''card_versions'\'', count(*) from card_versions union all select '\''edges'\'', count(*) from edges union all select '\''taxonomy_nodes'\'', count(*) from taxonomy_nodes union all select '\''node_taxonomy_assignments'\'', count(*) from node_taxonomy_assignments union all select '\''taxonomy_scope_projection_edges'\'', count(*) from taxonomy_scope_projection_edges union all select '\''taxonomy_card_scope_layouts'\'', count(*) from taxonomy_card_scope_layouts order by 1;"'
