"""
Abstract: Async SQLAlchemy session boundary for the knowledge corpus app.
Out of scope: Model declarations and repository-level query behavior.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from knowledge_corpus.config import Settings

SessionFactory = async_sessionmaker[AsyncSession]


def build_engine(*, database_url: str) -> AsyncEngine:
    return create_async_engine(
        database_url,
        pool_pre_ping=True,
    )


def build_session_factory(settings: Settings) -> tuple[AsyncEngine, SessionFactory]:
    engine = build_engine(database_url=settings.database_url)
    session_factory: SessionFactory = async_sessionmaker(
        engine,
        expire_on_commit=False,
        class_=AsyncSession,
    )
    return engine, session_factory
