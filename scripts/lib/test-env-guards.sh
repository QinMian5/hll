#!/usr/bin/env bash
# abstract: Shared guardrails for validating isolated test DB settings in scripts.
# out_of_scope: Docker stack lifecycle and pytest marker selection.

set -euo pipefail

assert_test_env_file_name() {
  local env_file="$1"
  if [[ "$(basename "$env_file")" != ".env.test" ]]; then
    echo "error: expected test env file '.env.test', got '$env_file'" >&2
    return 1
  fi
}

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
  SETTINGS_DOTENV_PATH="$env_file" APP_ENV=test \
    uv --directory "$api_dir" run python -c \
      "from core.config import get_settings; get_settings()" >/dev/null
}

build_migration_database_url() {
  local api_dir="$1"
  local env_file="$2"
  SETTINGS_DOTENV_PATH="$env_file" APP_ENV=test \
    uv --directory "$api_dir" run python -c \
      "from core.config import get_settings; print(get_settings().migration_database_url)"
}
