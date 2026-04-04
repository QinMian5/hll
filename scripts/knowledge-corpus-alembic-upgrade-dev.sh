#!/usr/bin/env bash
# abstract: Apply knowledge corpus Alembic migrations against the repository-managed dev database path.
# out_of_scope: Starting compose services and running pytest suites.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CORPUS_DIR="$ROOT_DIR/apps/knowledge_corpus"
COMPOSE_BASE="$ROOT_DIR/infra/compose/docker-compose.base.yml"
COMPOSE_DEV="$ROOT_DIR/infra/compose/docker-compose.dev.yml"
ENV_FILE="$ROOT_DIR/infra/env/.env.dev"
DEV_COMPOSE_PROJECT="${DEV_COMPOSE_PROJECT:-knowledge-dev-${USER:-local}}"

source "$ROOT_DIR/scripts/lib/test-env-guards.sh"

assert_test_env_file_exists "$ENV_FILE"

docker compose \
  -p "$DEV_COMPOSE_PROJECT" \
  --env-file "$ENV_FILE" \
  -f "$COMPOSE_BASE" \
  -f "$COMPOSE_DEV" \
  run --rm knowledge_corpus_migrate \
  alembic -c /app/apps/knowledge_corpus/alembic.ini upgrade head
