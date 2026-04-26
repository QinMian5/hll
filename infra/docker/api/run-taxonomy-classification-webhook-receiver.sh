#!/usr/bin/env sh
# abstract: Stable taxonomy-classification webhook receiver startup wrapper.
# out_of_scope: API serving, worker actor startup, and compose dependency orchestration.

set -eu

exec uvicorn entrypoints.taxonomy_classification_webhook_receiver:app --host 0.0.0.0 --port 8080
