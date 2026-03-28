#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONTRACT_SCRIPT="$ROOT_DIR/packages/contracts/scripts/export-openapi.sh"
GENERATE_TYPES_SCRIPT="$ROOT_DIR/packages/contracts/scripts/generate-types.sh"
GENERATE_CLIENT_SCRIPT="$ROOT_DIR/packages/contracts/scripts/generate-client.sh"

if [[ ! -x "$CONTRACT_SCRIPT" || ! -x "$GENERATE_TYPES_SCRIPT" || ! -x "$GENERATE_CLIENT_SCRIPT" ]]; then
  echo "contracts scripts are not ready; implement T05 first" >&2
  exit 1
fi

bash "$CONTRACT_SCRIPT"
bash "$GENERATE_TYPES_SCRIPT"
bash "$GENERATE_CLIENT_SCRIPT"
