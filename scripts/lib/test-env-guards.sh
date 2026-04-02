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
  uv --directory "$api_dir" run python -c \
    "from core.config import load_settings; load_settings(env_file='$env_file')" >/dev/null
}

build_migration_database_url() {
  local api_dir="$1"
  local env_file="$2"
  uv --directory "$api_dir" run python -c \
    "from core.config import load_settings; print(load_settings(env_file='$env_file').migration_database_url)"
}
