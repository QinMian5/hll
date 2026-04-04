"""
Abstract: Shared pytest support for the knowledge corpus test suite.
Out of scope: Real database lifecycle management and repository assertions.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
from pydantic import ValidationError
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine, AsyncSession

from knowledge_corpus.config import Settings, load_settings
from knowledge_corpus.db.session import build_engine


@pytest.fixture(scope="session")
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture(scope="session")
def test_settings() -> Settings:
    try:
        return load_settings()
    except ValidationError as exc:
        raise pytest.UsageError(
            "knowledge_corpus integration tests require process environment variables "
            "such as KNOWLEDGE_CORPUS_DATABASE_URL to be set before pytest startup."
        ) from exc


@pytest.fixture(scope="session")
async def db_engine(test_settings: Settings) -> AsyncIterator[AsyncEngine]:
    engine = build_engine(database_url=test_settings.knowledge_corpus_database_url)
    try:
        async with engine.connect() as connection:
            await connection.scalar(text("SELECT current_database()"))
        yield engine
    finally:
        await engine.dispose()


@pytest.fixture
async def db_connection(db_engine: AsyncEngine) -> AsyncIterator[AsyncConnection]:
    async with db_engine.connect() as connection:
        transaction = await connection.begin()
        try:
            yield connection
        finally:
            if transaction.is_active:
                await transaction.rollback()


@pytest.fixture
async def db_session(db_connection: AsyncConnection) -> AsyncIterator[AsyncSession]:
    session = AsyncSession(
        bind=db_connection,
        expire_on_commit=False,
        join_transaction_mode="create_savepoint",
    )
    try:
        yield session
    finally:
        await session.close()
