#!/usr/bin/env sh
# abstract: Stable worker role startup wrapper for Dramatiq consumer launch.
# out_of_scope: API process startup and HTTP serving behavior.

set -eu

exec dramatiq entrypoints.worker.entrypoint --path apps/api/src
