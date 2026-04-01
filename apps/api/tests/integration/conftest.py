"""
Abstract: Shared integration fixtures for isolated PostgreSQL-backed API tests.
Out of scope: Unit-test-only fixture behavior and API transport assertions.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator, Iterator
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncConnection,
    AsyncEngine,
    AsyncSession,
    create_async_engine,
)

import core.config as config_module
from core.config import Settings


@pytest.fixture(scope="session")
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture(scope="session")
def test_env_file(repo_root: Path) -> Path:
    explicit_env_file = os.getenv("SETTINGS_DOTENV_PATH")
    env_file = (
        Path(explicit_env_file).expanduser()
        if explicit_env_file
        else repo_root / "infra" / "env" / ".env.test"
    )
    if not env_file.exists():
        raise pytest.UsageError(
            f"missing integration test dotenv file: {env_file}. "
            "Create infra/env/.env.test with test-only DB settings."
        )
    return env_file


@pytest.fixture(scope="session")
def test_settings(test_env_file: Path) -> Iterator[Settings]:
    original_dotenv_path = os.environ.get("SETTINGS_DOTENV_PATH")
    original_app_env = os.environ.get("APP_ENV")
    os.environ["SETTINGS_DOTENV_PATH"] = str(test_env_file)
    os.environ["APP_ENV"] = "test"
    config_module.get_settings.cache_clear()
    settings = config_module.get_settings()
    config_module.validate_test_database_settings(settings)
    try:
        yield settings
    finally:
        config_module.get_settings.cache_clear()
        if original_dotenv_path is None:
            os.environ.pop("SETTINGS_DOTENV_PATH", None)
        else:
            os.environ["SETTINGS_DOTENV_PATH"] = original_dotenv_path
        if original_app_env is None:
            os.environ.pop("APP_ENV", None)
        else:
            os.environ["APP_ENV"] = original_app_env


@pytest.fixture(scope="session")
async def db_engine(test_settings: Settings) -> AsyncIterator[AsyncEngine]:
    engine = create_async_engine(
        test_settings.app_database_url,
        pool_pre_ping=True,
    )
    try:
        async with engine.connect() as connection:
            database_name = await connection.scalar(text("SELECT current_database()"))
            assert isinstance(database_name, str)
            assert database_name.endswith("_test")
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
