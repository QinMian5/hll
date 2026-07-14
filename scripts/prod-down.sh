#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_BASE="$ROOT_DIR/infra/compose/docker-compose.base.yml"
COMPOSE_PROD="$ROOT_DIR/infra/compose/docker-compose.prod.yml"

docker compose \
  -f "$COMPOSE_BASE" \
  -f "$COMPOSE_PROD" \
  down
