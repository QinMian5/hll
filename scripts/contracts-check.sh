#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERIFY_SCRIPT="$ROOT_DIR/packages/contracts/scripts/verify-up-to-date.sh"

if [[ ! -x "$VERIFY_SCRIPT" ]]; then
  echo "contracts verification script is not ready; implement T05 first" >&2
  exit 1
fi

bash "$VERIFY_SCRIPT"
