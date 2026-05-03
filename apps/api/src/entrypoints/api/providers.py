"""
Abstract: FastAPI dependency providers that compose module services at API runtime.
Out of scope: HTTP route declarations and worker actor execution loops.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Annotated, cast

from fastapi import Depends
from redis.asyncio import Redis
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
from modules.ingestion.repo import IngestionRequestRepo
from modules.ingestion.service import IngestionService
from modules.knowledge_graph.builders import build_knowledge_graph_service
from modules.knowledge_graph.ports import (
    KnowledgeGraphProjectionPort,
    KnowledgeGraphReadPort,
)
from modules.knowledge_graph.service import KnowledgeGraphService
from modules.search.cache import SearchRedisEmbeddingCache, SearchRedisResponseCache
from modules.search.service import SearchService
from modules.taxonomy.repo import TaxonomyRepo
from modules.taxonomy.service import TaxonomyService
from modules.taxonomy.view_cache import TaxonomyRedisProtocol, TaxonomyViewRedisCache
from shared.cache import RedisJsonProtocol
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
    embedding_client: Annotated[EmbeddingClient, Depends(get_embedding_client)],
) -> KnowledgeGraphService:
    return build_knowledge_graph_service(
        session=session,
        edge_title_mention_top_k=settings.edge_title_mention_top_k,
        edge_semantic_top_k=settings.edge_semantic_top_k,
        edge_semantic_min_strength=settings.edge_semantic_min_strength,
        edge_semantic_candidate_limit=settings.edge_semantic_candidate_limit,
        embedding_client=embedding_client,
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
        response_cache=SearchRedisResponseCache(
            redis=cast(RedisJsonProtocol, Redis.from_url(settings.redis_url)),
            ttl_seconds=settings.search_response_cache_ttl_seconds,
        ),
        embedding_cache=SearchRedisEmbeddingCache(
            redis=cast(RedisJsonProtocol, Redis.from_url(settings.redis_url)),
            ttl_seconds=settings.search_embedding_cache_ttl_seconds,
        ),
        embedding_model=settings.embedding_model,
    )


def get_taxonomy_service(
    session: Annotated[AsyncSession, Depends(get_async_session)],
    knowledge_projection_port: Annotated[
        KnowledgeGraphProjectionPort, Depends(get_knowledge_graph_service)
    ],
    settings: Annotated[Settings, Depends(get_settings)],
) -> TaxonomyService:
    return TaxonomyService(
        repo=TaxonomyRepo(session=session),
        knowledge_projection_port=knowledge_projection_port,
        view_cache=TaxonomyViewRedisCache(
            redis=cast(TaxonomyRedisProtocol, Redis.from_url(settings.redis_url)),
            descendant_count_ttl_seconds=settings.taxonomy_view_cache_ttl_seconds,
            view_response_ttl_seconds=settings.taxonomy_view_cache_ttl_seconds,
            card_scope_layout_ttl_seconds=settings.taxonomy_card_scope_layout_cache_ttl_seconds,
        ),
    )


def get_ingestion_service(
    settings: Annotated[Settings, Depends(get_settings)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> IngestionService:
    def _publish(task: IngestionTask) -> None:
        publish_ingestion_task(
            redis_url=settings.redis_url,
            task=task,
        )

    return IngestionService(
        task_publisher=_publish,
        ingestion_repo=IngestionRequestRepo(session=session),
    )
