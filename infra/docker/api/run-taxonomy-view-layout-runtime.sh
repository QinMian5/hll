#!/usr/bin/env sh
# abstract: Stable taxonomy view layout runtime startup wrapper.
# out_of_scope: API serving, worker actor startup, and compose dependency orchestration.

set -eu

exec python -m entrypoints.taxonomy_view_layout_runtime
