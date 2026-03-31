#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_BASE="$ROOT_DIR/infra/compose/docker-compose.base.yml"
COMPOSE_ENV="$ROOT_DIR/infra/env/.env.prod"
COMPOSE_PROD="$ROOT_DIR/infra/compose/docker-compose.prod.yml"

docker compose \
  --env-file "$COMPOSE_ENV" \
  -f "$COMPOSE_BASE" \
  -f "$COMPOSE_PROD" \
  up -d --build
