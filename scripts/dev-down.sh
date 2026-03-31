#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_BASE="$ROOT_DIR/infra/compose/docker-compose.base.yml"
COMPOSE_ENV="$ROOT_DIR/infra/env/.env.dev"
COMPOSE_DEV="$ROOT_DIR/infra/compose/docker-compose.dev.yml"

REMOVE_VOLUMES=false
if [[ "${1:-}" == "--volumes" ]]; then
  REMOVE_VOLUMES=true
fi

if [[ "$REMOVE_VOLUMES" == "true" ]]; then
  docker compose \
    --env-file "$COMPOSE_ENV" \
    -f "$COMPOSE_BASE" \
    -f "$COMPOSE_DEV" \
    down --volumes --remove-orphans
else
  docker compose \
    --env-file "$COMPOSE_ENV" \
    -f "$COMPOSE_BASE" \
    -f "$COMPOSE_DEV" \
    down --remove-orphans
fi
