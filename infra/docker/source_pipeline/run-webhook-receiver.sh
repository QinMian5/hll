#!/usr/bin/env sh
# abstract: Stable source-pipeline webhook receiver startup wrapper.
# out_of_scope: Compose topology and public ingress routing.

set -eu

exec uvicorn source_pipeline.entrypoints.webhook_receiver:app --host 0.0.0.0 --port 8080
