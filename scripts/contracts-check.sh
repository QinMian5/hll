#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERIFY_SCRIPT="$ROOT_DIR/packages/contracts/scripts/verify-up-to-date.sh"

bash "$VERIFY_SCRIPT"
