#!/usr/bin/env bash
# abstract: Generate a new Alembic revision from current code metadata in development mode.
# out_of_scope: Production migration execution and migration file post-edit decisions.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_BASE="$ROOT_DIR/infra/compose/docker-compose.base.yml"
COMPOSE_ENV="$ROOT_DIR/infra/env/.env.dev"
COMPOSE_DEV="$ROOT_DIR/infra/compose/docker-compose.dev.yml"

compose_args=(
  --env-file "$COMPOSE_ENV"
  -f "$COMPOSE_BASE"
  -f "$COMPOSE_DEV"
)

MSG="${MSG:-${1:-}}"
if [[ -z "$MSG" ]]; then
  echo "MSG is required. Example: make alembic-autogen MSG=\"enable_pgvector\""
  exit 1
fi

docker compose "${compose_args[@]}" \
  build api

docker compose "${compose_args[@]}" \
  run --rm migrate \
  alembic -c /app/apps/api/alembic.ini revision --autogenerate -m "$MSG"
