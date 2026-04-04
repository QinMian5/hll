"""
Abstract: Synchronous SQLAlchemy session boundary for the knowledge corpus app.
Out of scope: Model declarations and repository-level query behavior.
"""

from __future__ import annotations

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from knowledge_corpus.config import Settings


SessionFactory = sessionmaker[Session]


def build_engine(*, database_url: str) -> Engine:
    return create_engine(
        database_url,
        pool_pre_ping=True,
    )


def build_session_factory(settings: Settings) -> tuple[Engine, SessionFactory]:
    engine = build_engine(database_url=settings.knowledge_corpus_database_url)
    session_factory: SessionFactory = sessionmaker(
        engine,
        expire_on_commit=False,
        class_=Session,
    )
    return engine, session_factory
