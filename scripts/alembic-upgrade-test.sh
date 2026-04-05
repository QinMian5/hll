#!/usr/bin/env bash
# abstract: Apply Alembic migrations to the isolated test database.
# out_of_scope: Starting containers and running integration test suites.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
API_DIR="$ROOT_DIR/apps/api"
ENV_FILE="$ROOT_DIR/infra/env/.env.test"

source "$ROOT_DIR/scripts/lib/test-env-guards.sh"

assert_test_env_file_exists "$ENV_FILE"
set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a
validate_test_settings "$API_DIR"

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
