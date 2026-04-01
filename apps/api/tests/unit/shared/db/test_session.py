"""
Abstract: Unit tests for async SQLAlchemy engine/session runtime boundary.
Out of scope: Real database connectivity and migration lifecycle behavior.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

import core.config as config_module
import shared.db.session as session_module


@pytest.fixture
def configured_db_runtime(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    dotenv_file = tmp_path / ".env.dev"
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
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(config_module, "SETTINGS_DOTENV_PATH", dotenv_file)
    monkeypatch.setattr(session_module, "_engine", None)
    monkeypatch.setattr(session_module, "_async_session_factory", None)
    config_module.get_settings.cache_clear()

    yield

    config_module.get_settings.cache_clear()


@pytest.mark.usefixtures("configured_db_runtime")
def test_get_engine_is_lazy_singleton_and_async() -> None:
    engine = session_module.get_engine()
    assert isinstance(engine, AsyncEngine)
    assert engine is session_module.get_engine()
    assert engine.url.drivername == "postgresql+psycopg"
    assert engine.url.username == "knowledge_app"
    assert engine.url.password == "secret"
    assert engine.url.host == "postgres"
    assert engine.url.port == 5432
    assert engine.url.database == "knowledge"


@pytest.mark.usefixtures("configured_db_runtime")
def test_get_async_session_factory_uses_expected_defaults() -> None:
    session_factory = session_module.get_async_session_factory()
    assert session_factory.kw["bind"] is session_module.get_engine()
    assert session_factory.kw["expire_on_commit"] is False
    assert session_factory.class_ is AsyncSession


@pytest.mark.usefixtures("configured_db_runtime")
@pytest.mark.anyio
async def test_get_async_session_yields_asyncsession() -> None:
    session_generator = session_module.get_async_session()
    session = await anext(session_generator)
    try:
        assert isinstance(session, AsyncSession)
    finally:
        await session_generator.aclose()
