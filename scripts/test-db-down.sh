#!/usr/bin/env bash
# abstract: Stop the isolated test PostgreSQL + Redis container stack and optional test volumes.
# out_of_scope: Environment provisioning and migration execution.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_TEST="$ROOT_DIR/infra/compose/docker-compose.test.yml"
ENV_FILE="$ROOT_DIR/infra/env/.env.test"
TEST_COMPOSE_PROJECT="${TEST_COMPOSE_PROJECT:-knowledge-test-${USER:-local}}"

source "$ROOT_DIR/scripts/lib/test-env-guards.sh"

REMOVE_VOLUMES=false
if [[ "${1:-}" == "--volumes" ]]; then
  REMOVE_VOLUMES=true
fi

compose_args=(
  -p "$TEST_COMPOSE_PROJECT"
  -f "$COMPOSE_TEST"
)
if [[ -f "$ENV_FILE" ]]; then
  compose_args+=(--env-file "$ENV_FILE")
fi

if [[ "$REMOVE_VOLUMES" == "true" ]]; then
  docker compose "${compose_args[@]}" down --volumes --remove-orphans
else
  docker compose "${compose_args[@]}" down --remove-orphans
fi
