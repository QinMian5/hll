#!/usr/bin/env bash
# abstract: Apply Alembic migrations to development environment using migration role settings.
# out_of_scope: Migration generation and production environment rollout.

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

docker compose "${compose_args[@]}" \
  build api

docker compose "${compose_args[@]}" \
  run --rm migrate \
  alembic -c /app/apps/api/alembic.ini upgrade head
