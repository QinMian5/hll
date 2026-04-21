#!/usr/bin/env bash
# abstract: Apply source-pipeline Alembic migrations to the isolated test database path.
# out_of_scope: Starting containers and running integration test suites.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP_DIR="$ROOT_DIR/apps/source_pipeline"
COMPOSE_TEST="$ROOT_DIR/infra/compose/docker-compose.test.yml"
ENV_FILE="$ROOT_DIR/infra/env/.env.test"
TEST_COMPOSE_PROJECT="${TEST_COMPOSE_PROJECT:-knowledge-test-${USER:-local}}"

source "$ROOT_DIR/scripts/lib/test-env-guards.sh"

assert_test_env_file_exists "$ENV_FILE"
set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a
validate_source_pipeline_test_settings "$APP_DIR"

docker compose \
  -p "$TEST_COMPOSE_PROJECT" \
  --env-file "$ENV_FILE" \
  -f "$COMPOSE_TEST" \
  run --rm source_pipeline_migrate \
  alembic -c /app/apps/source_pipeline/alembic.ini upgrade head
