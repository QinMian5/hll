"""
Abstract: Shared integration fixtures for isolated PostgreSQL-backed API tests.
Out of scope: Unit-test-only fixture behavior and API transport assertions.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
from pathlib import Path

import pytest
from dotenv import dotenv_values
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
def test_env_file(repo_root: Path) -> Path:
    env_file = repo_root / "infra" / "env" / ".env.test"
    if not env_file.exists():
        raise pytest.UsageError(
            f"missing integration test dotenv file: {env_file}. "
            "Create infra/env/.env.test with test-only DB settings."
        )
    return env_file


@pytest.fixture(scope="session")
def test_settings(test_env_file: Path) -> Iterator[Settings]:
    monkeypatch = pytest.MonkeyPatch()
    for key, value in dotenv_values(test_env_file).items():
        if value is None:
            continue
        monkeypatch.setenv(key, value)
    try:
        yield Settings()
    finally:
        monkeypatch.undo()


@pytest.fixture(scope="session")
async def db_engine(test_settings: Settings) -> AsyncIterator[AsyncEngine]:
    engine = create_async_engine(
        test_settings.app_database_url,
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
