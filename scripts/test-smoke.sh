#!/usr/bin/env bash
set -euo pipefail
make -n bootstrap >/dev/null
make -n check >/dev/null
