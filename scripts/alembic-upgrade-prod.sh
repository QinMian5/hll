#!/usr/bin/env bash
# abstract: Apply all app Alembic migrations to production environment databases.
# out_of_scope: Migration generation and development environment workflows.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_BASE="$ROOT_DIR/infra/compose/docker-compose.base.yml"
COMPOSE_ENV="$ROOT_DIR/infra/env/.env.prod"
COMPOSE_PROD="$ROOT_DIR/infra/compose/docker-compose.prod.yml"

source "$ROOT_DIR/scripts/lib/test-env-guards.sh"
source "$ROOT_DIR/scripts/lib/postgres-role-bootstrap.sh"
source "$ROOT_DIR/scripts/lib/prod-volumes.sh"

compose_args=(
  --env-file "$COMPOSE_ENV"
  -f "$COMPOSE_BASE"
  -f "$COMPOSE_PROD"
)

ensure_prod_external_volumes

assert_test_env_file_exists "$COMPOSE_ENV"
set -a
# shellcheck disable=SC1090
source "$COMPOSE_ENV"
set +a
validate_test_settings "$ROOT_DIR/apps/api"
validate_knowledge_corpus_test_settings "$ROOT_DIR/apps/knowledge_corpus"
validate_source_pipeline_test_settings "$ROOT_DIR/apps/source_pipeline"
validate_mcp_migration_settings "$ROOT_DIR/apps/mcp"

converge_online_postgres_roles "${compose_args[@]}"

docker compose "${compose_args[@]}" up -d --build --wait \
  knowledge_corpus_db \
  source_pipeline_db \
  mcp_db

docker compose "${compose_args[@]}" build \
  api \
  knowledge_corpus_migrate \
  source_pipeline_migrate \
  mcp_migrate

docker compose "${compose_args[@]}" run --rm migrate
docker compose "${compose_args[@]}" run --rm knowledge_corpus_migrate
docker compose "${compose_args[@]}" run --rm source_pipeline_migrate
docker compose "${compose_args[@]}" run --rm mcp_migrate
