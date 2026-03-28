#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONTRACT_SCRIPT="$ROOT_DIR/packages/contracts/scripts/export-openapi.sh"
GENERATE_TYPES_SCRIPT="$ROOT_DIR/packages/contracts/scripts/generate-types.sh"
GENERATE_CLIENT_SCRIPT="$ROOT_DIR/packages/contracts/scripts/generate-client.sh"

bash "$CONTRACT_SCRIPT"
bash "$GENERATE_TYPES_SCRIPT"
bash "$GENERATE_CLIENT_SCRIPT"
