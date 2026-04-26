"""
Abstract: Shared runtime assembly primitives and singleton lifecycle for entrypoints.
Out of scope: FastAPI route transport behavior and domain business rules.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from functools import lru_cache

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from core.config import Settings, load_settings
from modules.ingestion import model as ingestion_model
from modules.knowledge_graph import model as knowledge_graph_model
from modules.taxonomy import model as taxonomy_model
from modules.taxonomy_classification import model as taxonomy_classification_model
from shared.db.session import (
    build_async_engine,
    build_async_session_factory,
    open_async_session,
)
from shared.integrations import EmbeddingClient, build_embedding_client

REGISTERED_MODEL_MODULES = (
    knowledge_graph_model,
    taxonomy_model,
    ingestion_model,
    taxonomy_classification_model,
)

_engine: AsyncEngine | None = None
_async_session_factory: async_sessionmaker[AsyncSession] | None = None
_embedding_client: EmbeddingClient | None = None


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return load_settings()


def get_engine(*, settings: Settings) -> AsyncEngine:
    global _engine
    if _engine is None:
        _engine = build_async_engine(database_url=settings.database_url)
    return _engine


def get_async_session_factory(
    *,
    settings: Settings,
) -> async_sessionmaker[AsyncSession]:
    global _async_session_factory
    if _async_session_factory is None:
        _async_session_factory = build_async_session_factory(engine=get_engine(settings=settings))
    return _async_session_factory


async def get_async_session(
    *,
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[AsyncSession]:
    async for session in open_async_session(session_factory=session_factory):
        yield session


def get_embedding_client(*, settings: Settings) -> EmbeddingClient:
    global _embedding_client
    if _embedding_client is None:
        _embedding_client = build_embedding_client(
            api_url=settings.embedding_api_url,
            model=settings.embedding_model,
            api_key=settings.embedding_api_key,
            timeout_seconds=settings.embedding_timeout_seconds,
        )
    return _embedding_client


@dataclass(slots=True, frozen=True)
class RuntimeDependencies:
    settings: Settings
    embedding_client: EmbeddingClient
    session_factory: async_sessionmaker[AsyncSession]


def get_runtime_dependencies() -> RuntimeDependencies:
    settings = get_settings()
    return RuntimeDependencies(
        settings=settings,
        embedding_client=get_embedding_client(settings=settings),
        session_factory=get_async_session_factory(settings=settings),
    )
