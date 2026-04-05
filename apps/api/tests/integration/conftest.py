"""
Abstract: Shared integration fixtures for isolated PostgreSQL-backed API tests.
Out of scope: Unit-test-only fixture behavior and API transport assertions.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
from pydantic import ValidationError
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncConnection,
    AsyncEngine,
    AsyncSession,
    create_async_engine,
)

from core.config import Settings


@pytest.fixture(scope="session")
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture(scope="session")
def test_settings() -> Settings:
    try:
        return Settings()
    except ValidationError as exc:
        raise pytest.UsageError(
            "API integration tests require process environment variables to be set "
            "before pytest startup."
        ) from exc


@pytest.fixture(scope="session")
async def db_engine(test_settings: Settings) -> AsyncIterator[AsyncEngine]:
    engine = create_async_engine(
        test_settings.database_url,
        pool_pre_ping=True,
    )
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
