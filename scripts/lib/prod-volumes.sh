#!/usr/bin/env bash
# abstract: Shared helpers for ensuring repository-managed production Docker volumes exist before compose entrypoints run.
# out_of_scope: Compose stack lifecycle, migration execution, and development volume handling.

set -euo pipefail

readonly PROD_EXTERNAL_VOLUMES=(
  "knowledge_postgres_prod_data"
  "knowledge_logto_postgres_prod_data"
  "knowledge_corpus_postgres_prod_data"
  "source_pipeline_postgres_prod_data"
  "knowledge_mcp_postgres_prod_data"
  "knowledge_redis_prod_data"
)

ensure_prod_external_volumes() {
  local volume_name
  for volume_name in "${PROD_EXTERNAL_VOLUMES[@]}"; do
    if ! docker volume inspect "$volume_name" >/dev/null 2>&1; then
      docker volume create "$volume_name" >/dev/null
    fi
  done
}
