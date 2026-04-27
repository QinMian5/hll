#!/usr/bin/env bash
# abstract: Apply all app Alembic migrations to isolated test databases.
# out_of_scope: Starting containers and running integration test suites.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
API_DIR="$ROOT_DIR/apps/api"
COMPOSE_TEST="$ROOT_DIR/infra/compose/docker-compose.test.yml"
ENV_FILE="$ROOT_DIR/infra/env/.env.test"

source "$ROOT_DIR/scripts/lib/test-env-guards.sh"

compose_args=(
  --env-file "$ENV_FILE"
  -f "$COMPOSE_TEST"
)

assert_test_env_file_exists "$ENV_FILE"
set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a
validate_test_settings "$API_DIR"
validate_knowledge_corpus_test_settings "$ROOT_DIR/apps/knowledge_corpus"
validate_source_pipeline_test_settings "$ROOT_DIR/apps/source_pipeline"
validate_mcp_migration_settings "$ROOT_DIR/apps/mcp"

bash "$ROOT_DIR/scripts/test-db-up.sh"

KNOWLEDGE_API_MIGRATION_DATABASE_URL="$(get_migration_database_url "$API_DIR")"

KNOWLEDGE_API_MIGRATION_DATABASE_URL="$KNOWLEDGE_API_MIGRATION_DATABASE_URL" \
  uv --directory "$API_DIR" run python - <<'PY'
import os
import time

import psycopg

database_url = os.environ["KNOWLEDGE_API_MIGRATION_DATABASE_URL"]
connect_url = database_url.replace("postgresql+psycopg://", "postgresql://", 1)
deadline = time.time() + 30

while True:
    try:
        with psycopg.connect(connect_url, connect_timeout=3) as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
        break
    except Exception:
        if time.time() >= deadline:
            raise
        time.sleep(1)
PY

(
  cd "$ROOT_DIR"
  uv --directory "$API_DIR" run alembic -c "$API_DIR/alembic.ini" upgrade head
)

docker compose "${compose_args[@]}" build \
  knowledge_corpus_migrate \
  source_pipeline_migrate \
  mcp_migrate

docker compose "${compose_args[@]}" run --rm knowledge_corpus_migrate
docker compose "${compose_args[@]}" run --rm source_pipeline_migrate
docker compose "${compose_args[@]}" run --rm mcp_migrate
