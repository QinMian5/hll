#!/usr/bin/env bash
# abstract: Execute integration tests against an isolated PostgreSQL + Redis test stack.
# out_of_scope: Unit-test execution and frontend test workflows.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
API_DIR="$ROOT_DIR/apps/api"
ENV_FILE="$ROOT_DIR/infra/env/.env.test"

source "$ROOT_DIR/scripts/lib/test-env-guards.sh"

assert_test_env_file_exists "$ENV_FILE"
validate_test_settings "$API_DIR" "$ENV_FILE"

cleanup() {
  if [[ "${KEEP_TEST_DB:-0}" == "1" ]]; then
    echo "[test-integration] KEEP_TEST_DB=1 -> skipping teardown"
    return
  fi
  bash "$ROOT_DIR/scripts/test-db-down.sh" --volumes
}

trap cleanup EXIT

echo "[test-integration] start isolated postgres+redis"
bash "$ROOT_DIR/scripts/test-db-up.sh"

echo "[test-integration] run migrations"
bash "$ROOT_DIR/scripts/alembic-upgrade-test.sh"

echo "[test-integration] run pytest integration db suite"
uv --directory "$API_DIR" run pytest tests/integration -m "integration and db and not slow"
