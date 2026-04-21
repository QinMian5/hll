#!/usr/bin/env sh
# abstract: Stable orchestrator role startup wrapper for source-pipeline polling.
# out_of_scope: API serving behavior and queue worker implementation.

set -eu

exec python -m source_pipeline.entrypoints.orchestrator
