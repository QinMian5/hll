"""
Abstract: Shared pytest support for PostgreSQL-backed source-pipeline tests.
Out of scope: Docker lifecycle management and queue integration behavior.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
from pydantic import ValidationError
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine, AsyncSession

from source_pipeline.config import Settings, load_settings
from source_pipeline.db.session import build_engine


@pytest.fixture(scope="session")
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture(scope="session")
def test_settings() -> Settings:
    try:
        return load_settings()
    except ValidationError as exc:
        raise pytest.UsageError(
            "source_pipeline integration tests require process environment variables "
            "such as SOURCE_PIPELINE_DATABASE_URL to be set before pytest startup."
        ) from exc


@pytest.fixture(scope="session")
async def db_engine(test_settings: Settings) -> AsyncIterator[AsyncEngine]:
    engine = build_engine(database_url=test_settings.database_url)
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
