"""
Abstract: FastAPI dependency providers that compose module services at API runtime.
Out of scope: HTTP route declarations and worker actor execution loops.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from core.config import Settings
from entrypoints.runtime import (
    get_async_session as open_runtime_async_session,
)
from entrypoints.runtime import (
    get_async_session_factory as get_runtime_async_session_factory,
)
from entrypoints.runtime import (
    get_embedding_client as get_runtime_embedding_client,
)
from entrypoints.runtime import (
    get_settings as get_runtime_settings,
)
from modules.ingestion.queue import IngestionTask, publish_ingestion_task
from modules.ingestion.service import IngestionService
from modules.knowledge_graph.builders import build_knowledge_graph_service
from modules.knowledge_graph.ports import KnowledgeGraphReadPort
from modules.knowledge_graph.service import KnowledgeGraphService
from modules.search.service import SearchService
from shared.integrations import EmbeddingClient


def get_settings() -> Settings:
    return get_runtime_settings()


def get_async_session_factory(
    settings: Annotated[Settings, Depends(get_settings)],
) -> async_sessionmaker[AsyncSession]:
    return get_runtime_async_session_factory(settings=settings)


async def get_async_session(
    session_factory: Annotated[
        async_sessionmaker[AsyncSession], Depends(get_async_session_factory)
    ],
) -> AsyncIterator[AsyncSession]:
    async for session in open_runtime_async_session(session_factory=session_factory):
        yield session


def get_embedding_client(
    settings: Annotated[Settings, Depends(get_settings)],
) -> EmbeddingClient:
    return get_runtime_embedding_client(settings=settings)


def get_knowledge_graph_service(
    session: Annotated[AsyncSession, Depends(get_async_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> KnowledgeGraphService:
    return build_knowledge_graph_service(
        session=session,
        edge_similarity_top_k=settings.edge_similarity_top_k,
        edge_similarity_min_strength=settings.edge_similarity_min_strength,
    )


def get_search_service(
    knowledge_graph_read_port: Annotated[
        KnowledgeGraphReadPort, Depends(get_knowledge_graph_service)
    ],
    embedding_client: Annotated[EmbeddingClient, Depends(get_embedding_client)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> SearchService:
    return SearchService(
        knowledge_graph_read_port=knowledge_graph_read_port,
        embedding_client=embedding_client,
        max_matched=settings.search_max_matched,
        max_connected=settings.search_max_connected,
    )


def get_ingestion_service(
    settings: Annotated[Settings, Depends(get_settings)],
) -> IngestionService:
    def _publish(task: IngestionTask) -> None:
        publish_ingestion_task(
            redis_url=settings.redis_url,
            task=task,
        )

    return IngestionService(
        task_publisher=_publish,
    )
