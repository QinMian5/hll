#!/usr/bin/env python3
"""
Abstract: Root-level launcher for the development taxonomy GraphView seed.
Out of scope: Seed implementation details and production data import.
"""

from __future__ import annotations

from entrypoints.ops.dev_seed_taxonomy_view import cli


if __name__ == "__main__":
    cli()
