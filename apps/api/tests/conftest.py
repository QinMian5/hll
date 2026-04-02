"""
Abstract: Shared pytest fixtures for API test suite.
Out of scope: Runtime application dependency wiring.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable, Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

from main import app as main_app

DependencyCallable = Callable[..., Any]
DependencyOverrides = dict[DependencyCallable, DependencyCallable]


@pytest.fixture(scope="session")
def repo_root() -> Path:
    current = Path(__file__).resolve()
    for candidate in (current, *current.parents):
        if (candidate / ".git").exists() and (candidate / "infra" / "env").exists():
            return candidate

    raise AssertionError(
        "Unable to locate repository root containing '.git' and 'infra/env'."
    )


@pytest.fixture
def dependency_overrides() -> DependencyOverrides:
    return {}


@pytest.fixture(scope="session")
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
def app(dependency_overrides: DependencyOverrides) -> Iterator[FastAPI]:
    main_app.dependency_overrides = dict(dependency_overrides)
    try:
        yield main_app
    finally:
        main_app.dependency_overrides = {}


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
async def async_client(app: FastAPI) -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as test_client:
        yield test_client
