#!/usr/bin/env bash
# abstract: Generate the internal Python contract client from the exported OpenAPI document.
# out_of_scope: OpenAPI export, TypeScript artifact generation, and handwritten client behavior.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
CONTRACTS_DIR="$ROOT_DIR/packages/contracts"
OPENAPI_INPUT_PATH="${OPENAPI_INPUT_PATH:-$CONTRACTS_DIR/openapi/openapi.json}"
OUTPUT_DIR="${GENERATED_PYTHON_CLIENT_OUTPUT_DIR:-$CONTRACTS_DIR/generated/python}"

python "$CONTRACTS_DIR/scripts/generate-python-client.py" \
  --openapi "$OPENAPI_INPUT_PATH" \
  --output-dir "$OUTPUT_DIR"

echo "Wrote generated Python client to $OUTPUT_DIR"
