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
    for key, value in {
        "KNOWLEDGE_API_DATABASE_URL": (
            "postgresql+psycopg://knowledge_app:secret@postgres:5432/knowledge"
        ),
        "KNOWLEDGE_API_REDIS_URL": "redis://redis:6379/0",
        "KNOWLEDGE_API_EMBEDDING_API_URL": "https://api.openai.com/v1/embeddings",
        "KNOWLEDGE_API_EMBEDDING_MODEL": "text-embedding-3-small",
        "KNOWLEDGE_API_EMBEDDING_API_KEY": "test-key",
        "KNOWLEDGE_API_EMBEDDING_TIMEOUT_SECONDS": "10",
        "KNOWLEDGE_API_SEARCH_MAX_MATCHED": "3",
        "KNOWLEDGE_API_SEARCH_MAX_CONNECTED": "7",
        "KNOWLEDGE_API_SEARCH_RESPONSE_CACHE_TTL_SECONDS": "60",
        "KNOWLEDGE_API_SEARCH_EMBEDDING_CACHE_TTL_SECONDS": "86400",
        "KNOWLEDGE_API_TAXONOMY_VIEW_CACHE_TTL_SECONDS": "60",
        "KNOWLEDGE_API_TAXONOMY_CARD_SCOPE_LAYOUT_CACHE_TTL_SECONDS": "600",
        "KNOWLEDGE_API_EDGE_TITLE_MENTION_TOP_K": "2",
        "KNOWLEDGE_API_EDGE_SEMANTIC_TOP_K": "4",
        "KNOWLEDGE_API_EDGE_SEMANTIC_MIN_STRENGTH": "0.61",
        "KNOWLEDGE_API_EDGE_SEMANTIC_CANDIDATE_LIMIT": "9",
        "KNOWLEDGE_API_LOG_LEVEL": "INFO",
        "KNOWLEDGE_API_LOG_FILE_PATH": "logs/api/app.log",
        "KNOWLEDGE_API_LOG_FILE_MAX_BYTES": "10485760",
        "KNOWLEDGE_API_LOG_FILE_BACKUP_COUNT": "5",
        "KNOWLEDGE_API_TAXONOMY_CLASSIFICATION_CURSOR_COMMAND": "cursor-agent",
        "KNOWLEDGE_API_TAXONOMY_CLASSIFICATION_CURSOR_WORKSPACE_ROOT": (
            "/tmp/knowledge-api-taxonomy-classification"
        ),
        "KNOWLEDGE_API_TAXONOMY_CLASSIFICATION_CURSOR_TIMEOUT_SECONDS": "180",
        "KNOWLEDGE_API_TAXONOMY_CLASSIFICATION_CURSOR_MAX_RETRIES": "3",
        "KNOWLEDGE_API_TAXONOMY_CLASSIFICATION_MAX_WORKERS": "8",
    }.items():
        monkeypatch.setenv(key, value)
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
