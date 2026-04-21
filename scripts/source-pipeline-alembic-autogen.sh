#!/usr/bin/env bash
# abstract: Generate a new source-pipeline Alembic revision from current metadata in development mode.
# out_of_scope: Applying migrations and resetting database state outside the dedicated source-pipeline path.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_BASE="$ROOT_DIR/infra/compose/docker-compose.base.yml"
COMPOSE_DEV="$ROOT_DIR/infra/compose/docker-compose.dev.yml"
ENV_FILE="$ROOT_DIR/infra/env/.env.dev"
DEV_COMPOSE_PROJECT="${DEV_COMPOSE_PROJECT:-knowledge-dev-${USER:-local}}"
APP_DIR="$ROOT_DIR/apps/source_pipeline"

source "$ROOT_DIR/scripts/lib/test-env-guards.sh"

MSG="${MSG:-${1:-}}"
if [[ -z "$MSG" ]]; then
  echo 'MSG is required. Example: bash scripts/source-pipeline-alembic-autogen.sh "initial_source_pipeline"' >&2
  exit 1
fi

assert_test_env_file_exists "$ENV_FILE"
set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a
validate_source_pipeline_test_settings "$APP_DIR"

docker compose \
  -p "$DEV_COMPOSE_PROJECT" \
  --env-file "$ENV_FILE" \
  -f "$COMPOSE_BASE" \
  -f "$COMPOSE_DEV" \
  run --rm source_pipeline_migrate \
  alembic -c /app/apps/source_pipeline/alembic.ini revision --autogenerate -m "$MSG"
