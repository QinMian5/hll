"""
Abstract: Shared pytest fixtures for API test suite.
Out of scope: Runtime application dependency wiring.
"""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture(scope="session")
def repo_root() -> Path:
    current = Path(__file__).resolve()
    for candidate in (current, *current.parents):
        if (candidate / ".git").exists() and (candidate / "infra" / "env").exists():
            return candidate

    raise AssertionError(
        "Unable to locate repository root containing '.git' and 'infra/env'."
    )
