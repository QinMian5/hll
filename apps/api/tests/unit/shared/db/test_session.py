"""
Abstract: Unit tests for async SQLAlchemy engine/session runtime boundary.
Out of scope: Real database connectivity and migration lifecycle behavior.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import cast

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

import shared.db.session as session_module
from core.config import Settings


@pytest.fixture
def runtime_settings(monkeypatch: pytest.MonkeyPatch) -> Settings:
    monkeypatch.setenv(
        "KNOWLEDGE_API_DATABASE_URL",
        "postgresql+psycopg://knowledge_app:secret@postgres:5432/knowledge",
    )
    monkeypatch.setenv("KNOWLEDGE_API_REDIS_URL", "redis://redis:6379/0")
    monkeypatch.setenv("KNOWLEDGE_API_EMBEDDING_API_URL", "https://api.openai.com/v1/embeddings")
    monkeypatch.setenv("KNOWLEDGE_API_EMBEDDING_MODEL", "text-embedding-3-small")
    monkeypatch.setenv("KNOWLEDGE_API_EMBEDDING_API_KEY", "test-key")
    monkeypatch.setenv("KNOWLEDGE_API_EMBEDDING_TIMEOUT_SECONDS", "10")
    monkeypatch.setenv("KNOWLEDGE_API_SEARCH_MAX_MATCHED", "5")
    monkeypatch.setenv("KNOWLEDGE_API_SEARCH_MAX_CONNECTED", "10")
    monkeypatch.setenv("KNOWLEDGE_API_EDGE_SIMILARITY_TOP_K", "10")
    monkeypatch.setenv("KNOWLEDGE_API_EDGE_SIMILARITY_MIN_STRENGTH", "0.37")
    monkeypatch.setenv("KNOWLEDGE_API_LOG_FILE_PATH", "logs/api/app.log")
    return Settings()


def test_build_async_engine_uses_expected_runtime_settings(
    runtime_settings: Settings,
) -> None:
    engine = session_module.build_async_engine(database_url=runtime_settings.database_url)
    assert isinstance(engine, AsyncEngine)
    assert engine.url.drivername == "postgresql+psycopg"
    assert engine.url.username == "knowledge_app"
    assert engine.url.password == "secret"
    assert engine.url.host == "postgres"
    assert engine.url.port == 5432
    assert engine.url.database == "knowledge"


def test_build_async_session_factory_uses_expected_defaults(
    runtime_settings: Settings,
) -> None:
    engine = session_module.build_async_engine(database_url=runtime_settings.database_url)
    session_factory = session_module.build_async_session_factory(engine=engine)
    assert session_factory.kw["bind"] is engine
    assert session_factory.kw["expire_on_commit"] is False
    assert session_factory.class_ is AsyncSession


@pytest.mark.anyio
async def test_open_async_session_yields_asyncsession(
    runtime_settings: Settings,
) -> None:
    engine = session_module.build_async_engine(database_url=runtime_settings.database_url)
    session_factory = session_module.build_async_session_factory(engine=engine)
    session_generator = cast(
        AsyncGenerator[AsyncSession],
        session_module.open_async_session(session_factory=session_factory),
    )
    session = await anext(session_generator)
    try:
        assert isinstance(session, AsyncSession)
    finally:
        await session_generator.aclose()
