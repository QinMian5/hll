#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_BASE="$ROOT_DIR/infra/compose/docker-compose.base.yml"
COMPOSE_ENV="$ROOT_DIR/infra/env/.env.dev"
COMPOSE_DEV="$ROOT_DIR/infra/compose/docker-compose.dev.yml"

compose_args=(
  --env-file "$COMPOSE_ENV"
  -f "$COMPOSE_BASE"
  -f "$COMPOSE_DEV"
)

# `migrate` and `knowledge_corpus_migrate` are one-shot jobs. If an older
# failed container is reused, `service_completed_successfully` can stay blocked.
docker compose "${compose_args[@]}" rm -f migrate knowledge_corpus_migrate >/dev/null 2>&1 || true

if ! docker compose "${compose_args[@]}" up -d --build; then
  echo "[dev-up] migrate service failed. Recent logs:" >&2
  docker compose "${compose_args[@]}" logs migrate --tail 200 >&2 || true
  echo "[dev-up] knowledge_corpus_migrate service logs:" >&2
  docker compose "${compose_args[@]}" logs knowledge_corpus_migrate --tail 200 >&2 || true
  exit 1
fi
