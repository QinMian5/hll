#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
API_DIR="$ROOT_DIR/apps/api"
OUTPUT_PATH="${OPENAPI_OUTPUT_PATH:-$ROOT_DIR/packages/contracts/openapi/openapi.json}"

mkdir -p "$(dirname "$OUTPUT_PATH")"

uv run --project "$API_DIR" python - "$OUTPUT_PATH" <<'PY'
from __future__ import annotations

import json
import sys
from pathlib import Path

from entrypoints.api.app import create_app


def main() -> None:
    output_path = Path(sys.argv[1]).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    app = create_app()
    openapi = app.openapi()
    output_path.write_text(
        json.dumps(openapi, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote OpenAPI to {output_path}")


if __name__ == "__main__":
    main()
PY
