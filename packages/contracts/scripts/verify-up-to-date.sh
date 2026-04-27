#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
CONTRACTS_DIR="$ROOT_DIR/packages/contracts"
OPENAPI_FILE="$CONTRACTS_DIR/openapi/openapi.json"
TYPES_FILE="$CONTRACTS_DIR/generated/types.ts"
CLIENT_FILE="$CONTRACTS_DIR/generated/client.ts"
PYTHON_CLIENT_DIR="$CONTRACTS_DIR/generated/python"

for artifact in "$OPENAPI_FILE" "$TYPES_FILE" "$CLIENT_FILE"; do
  if [[ ! -f "$artifact" ]]; then
    echo "Missing generated artifact: $artifact" >&2
    echo "Run 'pnpm export', 'pnpm generate:types', and 'pnpm generate:client' first." >&2
    exit 1
  fi
done

if [[ ! -d "$PYTHON_CLIENT_DIR" ]]; then
  echo "Missing generated artifact: $PYTHON_CLIENT_DIR" >&2
  echo "Run 'pnpm export', 'pnpm generate:types', 'pnpm generate:client', and 'pnpm generate:python' first." >&2
  exit 1
fi

temp_dir="$(mktemp -d "$CONTRACTS_DIR/.tmp.verify.XXXXXX")"
trap 'rm -rf "$temp_dir"' EXIT

expected_openapi="$temp_dir/openapi.json"
expected_types="$temp_dir/types.ts"
expected_client="$temp_dir/client.ts"
expected_python_client="$temp_dir/python"

OPENAPI_OUTPUT_PATH="$expected_openapi" bash "$CONTRACTS_DIR/scripts/export-openapi.sh"
OPENAPI_INPUT_PATH="$expected_openapi" \
GENERATED_TYPES_OUTPUT_PATH="$expected_types" \
  bash "$CONTRACTS_DIR/scripts/generate-types.sh"
GENERATED_TYPES_INPUT_PATH="$expected_types" \
GENERATED_CLIENT_OUTPUT_PATH="$expected_client" \
  bash "$CONTRACTS_DIR/scripts/generate-client.sh"
OPENAPI_INPUT_PATH="$expected_openapi" \
GENERATED_PYTHON_CLIENT_OUTPUT_DIR="$expected_python_client" \
  bash "$CONTRACTS_DIR/scripts/generate-python-client.sh"

for pair in \
  "$OPENAPI_FILE:$expected_openapi" \
  "$TYPES_FILE:$expected_types" \
  "$CLIENT_FILE:$expected_client"; do
  current_file="${pair%%:*}"
  expected_file="${pair##*:}"
  if ! cmp -s "$current_file" "$expected_file"; then
    echo "Generated artifact is stale: $current_file" >&2
    diff -u "$current_file" "$expected_file" || true
    exit 1
  fi
done

if ! diff -ru -x __pycache__ -x '*.pyc' "$PYTHON_CLIENT_DIR" "$expected_python_client"; then
  echo "Generated artifact is stale: $PYTHON_CLIENT_DIR" >&2
  exit 1
fi

echo "Contracts artifacts are up to date."
