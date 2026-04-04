#!/usr/bin/env bash
# abstract: Apply knowledge corpus Alembic migrations to the isolated test database path.
# out_of_scope: Starting containers and running integration test suites.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_TEST="$ROOT_DIR/infra/compose/docker-compose.test.yml"
ENV_FILE="$ROOT_DIR/infra/env/.env.test"
TEST_COMPOSE_PROJECT="${TEST_COMPOSE_PROJECT:-knowledge-test-${USER:-local}}"

source "$ROOT_DIR/scripts/lib/test-env-guards.sh"

assert_test_env_file_exists "$ENV_FILE"
set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a
validate_knowledge_corpus_test_settings "$ROOT_DIR/apps/knowledge_corpus"

docker compose \
  -p "$TEST_COMPOSE_PROJECT" \
  --env-file "$ENV_FILE" \
  -f "$COMPOSE_TEST" \
  run --rm knowledge_corpus_migrate \
  alembic -c /app/apps/knowledge_corpus/alembic.ini upgrade head
