#!/usr/bin/env sh
# abstract: Stable taxonomy-classification runtime startup wrapper.
# out_of_scope: API serving, worker actor startup, and compose dependency orchestration.

set -eu

exec python -m entrypoints.taxonomy_classification_runtime
