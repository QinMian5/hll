"""
Abstract: Unit tests for async SQLAlchemy engine/session runtime boundary.
Out of scope: Real database connectivity and migration lifecycle behavior.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from pathlib import Path
from typing import cast

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

import shared.db.session as session_module
from core.config import Settings


@pytest.fixture
def runtime_settings(tmp_path: Path) -> Settings:
    dotenv_file = tmp_path / ".env.runtime"
    dotenv_file.write_text(
        "\n".join(
            [
                "DB_HOST=postgres",
                "DB_PORT=5432",
                "DB_NAME=knowledge",
                "APP_DB_USER=knowledge_app",
                "APP_DB_PASSWORD=secret",
                "MIGRATION_DB_USER=knowledge_migration",
                "MIGRATION_DB_PASSWORD=secret_m",
                "REDIS_URL=redis://redis:6379/0",
                "EMBEDDING_API_URL=https://api.openai.com/v1/embeddings",
                "EMBEDDING_MODEL=text-embedding-3-small",
                "EMBEDDING_API_KEY=test-key",
                "EMBEDDING_TIMEOUT_SECONDS=10",
                "SEARCH_MAX_MATCHED=5",
                "SEARCH_MAX_CONNECTED=10",
                "EDGE_SIMILARITY_TOP_K=10",
                "EDGE_SIMILARITY_MIN_STRENGTH=0.6",
            ]
        ),
        encoding="utf-8",
    )
    return Settings(_env_file=dotenv_file)


def test_build_async_engine_uses_expected_runtime_settings(
    runtime_settings: Settings,
) -> None:
    engine = session_module.build_async_engine(
        database_url=runtime_settings.app_database_url
    )
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
    engine = session_module.build_async_engine(
        database_url=runtime_settings.app_database_url
    )
    session_factory = session_module.build_async_session_factory(engine=engine)
    assert session_factory.kw["bind"] is engine
    assert session_factory.kw["expire_on_commit"] is False
    assert session_factory.class_ is AsyncSession


@pytest.mark.anyio
async def test_open_async_session_yields_asyncsession(
    runtime_settings: Settings,
) -> None:
    engine = session_module.build_async_engine(
        database_url=runtime_settings.app_database_url
    )
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
