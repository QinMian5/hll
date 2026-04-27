#!/usr/bin/env bash
# abstract: Start the repository production Docker Compose stack.
# out_of_scope: Development runtime startup and test database lifecycle.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_BASE="$ROOT_DIR/infra/compose/docker-compose.base.yml"
COMPOSE_ENV="$ROOT_DIR/infra/env/.env.prod"
COMPOSE_PROD="$ROOT_DIR/infra/compose/docker-compose.prod.yml"

source "$ROOT_DIR/scripts/lib/postgres-role-bootstrap.sh"
source "$ROOT_DIR/scripts/lib/prod-volumes.sh"

compose_args=(
  --env-file "$COMPOSE_ENV"
  -f "$COMPOSE_BASE"
  -f "$COMPOSE_PROD"
)

ensure_prod_external_volumes

# Role provisioning belongs to database bootstrap, not Alembic migrations.
converge_online_postgres_roles "${compose_args[@]}"

# `migrate`, `knowledge_corpus_migrate`, `source_pipeline_migrate`, and `mcp_migrate` are one-shot jobs. If an older
# failed container is reused, `service_completed_successfully` can stay blocked.
docker compose "${compose_args[@]}" rm -f migrate knowledge_corpus_migrate source_pipeline_migrate mcp_migrate >/dev/null 2>&1 || true

if ! docker compose "${compose_args[@]}" up -d --build; then
  echo "[prod-up] migrate service logs:" >&2
  docker compose "${compose_args[@]}" logs migrate --tail 200 >&2 || true
  echo "[prod-up] knowledge_corpus_migrate service logs:" >&2
  docker compose "${compose_args[@]}" logs knowledge_corpus_migrate --tail 200 >&2 || true
  echo "[prod-up] source_pipeline_migrate service logs:" >&2
  docker compose "${compose_args[@]}" logs source_pipeline_migrate --tail 200 >&2 || true
  echo "[prod-up] mcp_migrate service logs:" >&2
  docker compose "${compose_args[@]}" logs mcp_migrate --tail 200 >&2 || true
  exit 1
fi
