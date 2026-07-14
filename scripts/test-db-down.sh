#!/usr/bin/env bash
# abstract: Stop the isolated test PostgreSQL + Redis container stack and optional test volumes.
# out_of_scope: Environment provisioning and migration execution.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_TEST="$ROOT_DIR/infra/compose/docker-compose.test.yml"

REMOVE_VOLUMES=false
if [[ "${1:-}" == "--volumes" ]]; then
  REMOVE_VOLUMES=true
fi

compose_args=(
  -f "$COMPOSE_TEST"
)

if [[ "$REMOVE_VOLUMES" == "true" ]]; then
  docker compose "${compose_args[@]}" down --volumes --remove-orphans
else
  docker compose "${compose_args[@]}" down --remove-orphans
fi
