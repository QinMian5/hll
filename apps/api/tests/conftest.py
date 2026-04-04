"""
Abstract: Shared pytest fixtures for API test suite.
Out of scope: Runtime application dependency wiring.
"""

from __future__ import annotations

import importlib
from collections.abc import AsyncIterator, Callable, Iterator
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

DependencyCallable = Callable[..., Any]
DependencyOverrides = dict[DependencyCallable, DependencyCallable]

DEFAULT_APP_ENV = {
    "APP_DATABASE_URL": "postgresql+psycopg://knowledge_app:secret@postgres:5432/knowledge",
    "REDIS_URL": "redis://redis:6379/0",
    "EMBEDDING_API_URL": "https://api.openai.com/v1/embeddings",
    "EMBEDDING_MODEL": "text-embedding-3-small",
    "EMBEDDING_API_KEY": "test-key",
    "EMBEDDING_TIMEOUT_SECONDS": "10",
    "SEARCH_MAX_MATCHED": "5",
    "SEARCH_MAX_CONNECTED": "10",
    "EDGE_SIMILARITY_TOP_K": "10",
    "EDGE_SIMILARITY_MIN_STRENGTH": "0.8",
    "LOG_FILE_PATH": "logs/api/app.log",
}


@pytest.fixture
def dependency_overrides() -> DependencyOverrides:
    return {}


@pytest.fixture(scope="session")
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
def app(
    dependency_overrides: DependencyOverrides,
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[FastAPI]:
    for key, value in DEFAULT_APP_ENV.items():
        monkeypatch.setenv(key, value)

    import entrypoints.api.bootstrap as api_bootstrap
    from entrypoints.runtime import get_settings

    get_settings.cache_clear()
    importlib.reload(api_bootstrap)
    main_app = api_bootstrap.build_app()

    main_app.dependency_overrides = dict(dependency_overrides)
    try:
        yield main_app
    finally:
        main_app.dependency_overrides = {}
        get_settings.cache_clear()


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
