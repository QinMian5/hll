#!/usr/bin/env bash
# abstract: Shared guardrails for validating test runtime settings in scripts.
# out_of_scope: Docker stack lifecycle and pytest marker selection.

set -euo pipefail

assert_test_env_file_exists() {
  local env_file="$1"
  if [[ ! -f "$env_file" ]]; then
    echo "error: missing test env file: $env_file" >&2
    return 1
  fi
}

validate_test_settings() {
  local api_dir="$1"
  local env_file="$2"
  (
    set -a
    # shellcheck disable=SC1090
    source "$env_file"
    set +a
    uv --directory "$api_dir" run python -c \
      "from core.config import load_settings, load_migration_settings; load_settings(); load_migration_settings()" >/dev/null
  )
}

get_migration_database_url() {
  local api_dir="$1"
  local env_file="$2"
  (
    set -a
    # shellcheck disable=SC1090
    source "$env_file"
    set +a
    uv --directory "$api_dir" run python -c \
      "from core.config import load_migration_settings; print(load_migration_settings().migration_database_url)"
  )
}
