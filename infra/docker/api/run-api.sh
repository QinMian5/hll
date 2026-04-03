#!/usr/bin/env sh
# abstract: Stable API role startup wrapper for uvicorn process launch.
# out_of_scope: Worker process startup and compose dependency orchestration.

set -eu

if [ "${API_RELOAD:-0}" = "1" ]; then
  exec uv run uvicorn main:app --app-dir src --host 0.0.0.0 --port 8000 --reload
fi

exec uv run uvicorn main:app --app-dir src --host 0.0.0.0 --port 8000
