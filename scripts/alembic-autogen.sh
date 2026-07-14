#!/usr/bin/env bash
# abstract: Generate an app-selected Alembic revision from current metadata in development mode.
# out_of_scope: Production migration execution and migration file post-edit decisions.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_BASE="$ROOT_DIR/infra/compose/docker-compose.base.yml"
COMPOSE_ENV="$ROOT_DIR/infra/env/.env.dev"
COMPOSE_DEV="$ROOT_DIR/infra/compose/docker-compose.dev.yml"
APP="${APP:-api}"

source "$ROOT_DIR/scripts/lib/test-env-guards.sh"
source "$ROOT_DIR/scripts/lib/postgres-role-bootstrap.sh"
source "$ROOT_DIR/scripts/lib/runtime-env.sh"

compose_args=(
  -f "$COMPOSE_BASE"
  -f "$COMPOSE_DEV"
)

MSG="${MSG:-${1:-}}"
if [[ -z "$MSG" ]]; then
  echo "MSG is required. Example: make alembic-autogen APP=api MSG=\"enable_pgvector\""
  exit 1
fi

assert_test_env_file_exists "$COMPOSE_ENV"
set -a
# shellcheck disable=SC1090
source "$COMPOSE_ENV"
set +a

materialize_runtime_env dev "$COMPOSE_ENV"

case "$APP" in
  api)
    validate_test_settings "$ROOT_DIR/apps/api"
    converge_online_postgres_roles "${compose_args[@]}"
    docker compose "${compose_args[@]}" build api
    docker compose "${compose_args[@]}" run --rm migrate \
      alembic -c /app/apps/api/alembic.ini revision --autogenerate -m "$MSG"
    ;;
  knowledge_corpus)
    validate_knowledge_corpus_test_settings "$ROOT_DIR/apps/knowledge_corpus"
    docker compose "${compose_args[@]}" up -d --build --wait knowledge_corpus_db
    docker compose "${compose_args[@]}" run --rm knowledge_corpus_migrate \
      alembic -c /app/apps/knowledge_corpus/alembic.ini revision --autogenerate -m "$MSG"
    ;;
  source_pipeline)
    validate_source_pipeline_test_settings "$ROOT_DIR/apps/source_pipeline"
    docker compose "${compose_args[@]}" up -d --build --wait source_pipeline_db
    docker compose "${compose_args[@]}" run --rm source_pipeline_migrate \
      alembic -c /app/apps/source_pipeline/alembic.ini revision --autogenerate -m "$MSG"
    ;;
  mcp)
    validate_mcp_migration_settings "$ROOT_DIR/apps/mcp"
    docker compose "${compose_args[@]}" up -d --build --wait mcp_db
    docker compose "${compose_args[@]}" build mcp_migrate
    docker compose "${compose_args[@]}" run --rm mcp_migrate \
      alembic -c /app/apps/mcp/alembic.ini revision --autogenerate -m "$MSG"
    ;;
  *)
    echo "Unsupported APP: $APP. Expected api, knowledge_corpus, source_pipeline, or mcp." >&2
    exit 1
    ;;
esac
