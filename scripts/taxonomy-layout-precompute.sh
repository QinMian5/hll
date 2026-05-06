#!/usr/bin/env bash
# abstract: Precompute taxonomy card-scope layouts through the API operator runtime.
# out_of_scope: Public API serving, scheduling, and alternate layout persistence.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_BASE="$ROOT_DIR/infra/compose/docker-compose.base.yml"
COMPOSE_PRECOMPUTE="$ROOT_DIR/infra/compose/docker-compose.taxonomy-layout-precompute.yml"
ENVIRONMENT="${TAXONOMY_LAYOUT_PRECOMPUTE_ENVIRONMENT:-dev}"
PRECOMPUTE_ARGS=()
RUN_ARGS=(--rm)

while [[ $# -gt 0 ]]; do
  case "$1" in
    --environment)
      if [[ $# -lt 2 ]]; then
        echo "error: --environment requires dev or prod" >&2
        exit 2
      fi
      ENVIRONMENT="$2"
      shift 2
      ;;
    --environment=*)
      ENVIRONMENT="${1#*=}"
      shift
      ;;
    *)
      PRECOMPUTE_ARGS+=("$1")
      shift
      ;;
  esac
done

case "$ENVIRONMENT" in
  dev)
    COMPOSE_ENV="$ROOT_DIR/infra/env/.env.dev"
    COMPOSE_OVERLAY="$ROOT_DIR/infra/compose/docker-compose.dev.yml"
    ;;
  prod)
    COMPOSE_ENV="$ROOT_DIR/infra/env/.env.prod"
    COMPOSE_OVERLAY="$ROOT_DIR/infra/compose/docker-compose.prod.yml"
    RUN_ARGS+=(--no-deps)
    source "$ROOT_DIR/scripts/lib/prod-volumes.sh"
    ensure_prod_external_volumes
    ;;
  *)
    echo "error: --environment must be dev or prod, got: $ENVIRONMENT" >&2
    exit 2
    ;;
esac

if [[ ! -f "$COMPOSE_ENV" ]]; then
  echo "error: env file does not exist: $COMPOSE_ENV" >&2
  exit 1
fi

compose_args=(
  --env-file "$COMPOSE_ENV"
  -f "$COMPOSE_BASE"
  -f "$COMPOSE_OVERLAY"
  -f "$COMPOSE_PRECOMPUTE"
)

exec docker compose "${compose_args[@]}" run "${RUN_ARGS[@]}" \
  --volume "$ROOT_DIR/apps/api/src:/app/apps/api/src:ro" \
  taxonomy_view_layout_runtime \
  python -m entrypoints.ops.taxonomy_layout_precompute "${PRECOMPUTE_ARGS[@]}"
