#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
OPENAPI_INPUT_PATH="${OPENAPI_INPUT_PATH:-$ROOT_DIR/packages/contracts/openapi/openapi.json}"
OUTPUT_PATH="${GENERATED_TYPES_OUTPUT_PATH:-$ROOT_DIR/packages/contracts/generated/types.ts}"

if [[ ! -f "$OPENAPI_INPUT_PATH" ]]; then
  echo "Missing OpenAPI source artifact: $OPENAPI_INPUT_PATH" >&2
  echo "Run 'pnpm export' first." >&2
  exit 1
fi

mkdir -p "$(dirname "$OUTPUT_PATH")"

pnpm exec openapi-typescript "$OPENAPI_INPUT_PATH" --output "$OUTPUT_PATH"
echo "Wrote generated TypeScript types to $OUTPUT_PATH"
