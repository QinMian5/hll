"""
Abstract: Async SQLAlchemy session boundary for the source-pipeline app.
Out of scope: Model declarations and runtime step orchestration behavior.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from source_pipeline.config import SourcePipelineSettings

SessionFactory = async_sessionmaker[AsyncSession]


def build_engine(*, database_url: str) -> AsyncEngine:
    return create_async_engine(
        database_url,
        pool_pre_ping=True,
    )


def build_session_factory(settings: SourcePipelineSettings) -> tuple[AsyncEngine, SessionFactory]:
    engine = build_engine(database_url=settings.database_url)
    session_factory: SessionFactory = async_sessionmaker(
        engine,
        expire_on_commit=False,
        class_=AsyncSession,
    )
    return engine, session_factory
