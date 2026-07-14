#!/usr/bin/env bash
# abstract: Start an isolated PostgreSQL + Redis container stack dedicated to tests.
# out_of_scope: Running migrations and executing pytest suites.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_TEST="$ROOT_DIR/infra/compose/docker-compose.test.yml"
ENV_FILE="$ROOT_DIR/infra/env/.env.test"

source "$ROOT_DIR/scripts/lib/test-env-guards.sh"
source "$ROOT_DIR/scripts/lib/postgres-role-bootstrap.sh"
source "$ROOT_DIR/scripts/lib/runtime-env.sh"

compose_args=(
  -f "$COMPOSE_TEST"
)

assert_test_env_file_exists "$ENV_FILE"
set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a
validate_test_settings "$ROOT_DIR/apps/api"
validate_knowledge_corpus_test_settings "$ROOT_DIR/apps/knowledge_corpus"
validate_source_pipeline_test_settings "$ROOT_DIR/apps/source_pipeline"
validate_mcp_migration_settings "$ROOT_DIR/apps/mcp"

materialize_runtime_env test "$ENV_FILE"
converge_online_postgres_roles "${compose_args[@]}"

docker compose "${compose_args[@]}" up -d --build --wait knowledge_corpus_db source_pipeline_db mcp_db redis
