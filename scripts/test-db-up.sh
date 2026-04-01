#!/usr/bin/env bash
# abstract: Start an isolated PostgreSQL container stack dedicated to tests.
# out_of_scope: Running migrations and executing pytest suites.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_TEST="$ROOT_DIR/infra/compose/docker-compose.test.yml"
ENV_FILE="$ROOT_DIR/infra/env/.env.test"
TEST_COMPOSE_PROJECT="${TEST_COMPOSE_PROJECT:-knowledge-test-${USER:-local}}"

source "$ROOT_DIR/scripts/lib/test-env-guards.sh"

assert_test_env_file_name "$ENV_FILE"
assert_test_env_file_exists "$ENV_FILE"
validate_test_settings "$ROOT_DIR/apps/api" "$ENV_FILE"

docker compose \
  -p "$TEST_COMPOSE_PROJECT" \
  --env-file "$ENV_FILE" \
  -f "$COMPOSE_TEST" \
  up -d --build --wait
