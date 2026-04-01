"""
Abstract: Runtime async SQLAlchemy engine/session boundary for API code paths.
Out of scope: Domain model definitions and migration execution workflow.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from core.config import get_settings

_engine: AsyncEngine | None = None
_async_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        settings = get_settings()
        _engine = create_async_engine(
            settings.app_database_url,
            pool_pre_ping=True,
        )
    return _engine


def get_async_session_factory() -> async_sessionmaker[AsyncSession]:
    global _async_session_factory
    if _async_session_factory is None:
        _async_session_factory = async_sessionmaker(
            get_engine(),
            expire_on_commit=False,
            class_=AsyncSession,
        )
    return _async_session_factory


async def get_async_session() -> AsyncIterator[AsyncSession]:
    async_session_factory = get_async_session_factory()
    async with async_session_factory() as session:
        yield session
