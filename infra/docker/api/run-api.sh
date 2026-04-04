#!/usr/bin/env sh
# abstract: Stable API role startup wrapper for uvicorn process launch.
# out_of_scope: Worker process startup and compose dependency orchestration.

set -eu

if [ "${API_RELOAD:-0}" = "1" ]; then
  exec uvicorn entrypoints.api.bootstrap:build_app --factory --app-dir apps/api/src --host 0.0.0.0 --port 8000 --reload
fi

exec uvicorn entrypoints.api.bootstrap:build_app --factory --app-dir apps/api/src --host 0.0.0.0 --port 8000
