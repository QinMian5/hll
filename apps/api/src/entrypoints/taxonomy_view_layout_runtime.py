"""
Abstract: Long-running taxonomy view layout background runtime entrypoint.
Out of scope: HTTP route handling and taxonomy layout algorithm design.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from dataclasses import dataclass
from typing import Protocol, cast

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from core.config import (
    TaxonomyViewLayoutRuntimeSettings,
    load_taxonomy_view_layout_runtime_settings,
)
from modules.knowledge_graph.builders import build_knowledge_graph_service
from modules.taxonomy.repo import TaxonomyRepo
from modules.taxonomy.service import TaxonomyService
from modules.taxonomy.view_cache import TaxonomyRedisProtocol, TaxonomyViewRedisCache
from shared.db.session import build_async_engine, build_async_session_factory

logger = logging.getLogger(__name__)
TAXONOMY_VIEW_LAYOUT_POLL_INTERVAL_SECONDS = 1.0


class TaxonomyLayoutComputeCache(Protocol):
    async def claim_leaf_layout_compute(self) -> int | None: ...

    async def complete_leaf_layout_compute(self, *, leaf_id: int) -> None: ...


class TaxonomyLayoutComputeService(Protocol):
    async def build_and_cache_leaf_layout(self, *, leaf_id: int) -> object: ...


TaxonomyLayoutServiceFactory = Callable[
    [],
    AbstractAsyncContextManager[TaxonomyLayoutComputeService],
]


@dataclass(slots=True, frozen=True)
class TaxonomyViewLayoutRuntime:
    settings: TaxonomyViewLayoutRuntimeSettings
    engine: AsyncEngine
    session_factory: async_sessionmaker[AsyncSession]
    view_cache: TaxonomyViewRedisCache
    redis: Redis


def build_runtime() -> TaxonomyViewLayoutRuntime:
    settings = load_taxonomy_view_layout_runtime_settings()
    engine = build_async_engine(database_url=settings.database_url)
    session_factory = build_async_session_factory(engine=engine)
    redis = Redis.from_url(settings.redis_url)
    return TaxonomyViewLayoutRuntime(
        settings=settings,
        engine=engine,
        session_factory=session_factory,
        view_cache=TaxonomyViewRedisCache(
            redis=cast(TaxonomyRedisProtocol, redis),
            descendant_count_ttl_seconds=settings.taxonomy_view_cache_ttl_seconds,
            view_response_ttl_seconds=settings.taxonomy_view_cache_ttl_seconds,
            leaf_layout_ttl_seconds=settings.taxonomy_leaf_layout_cache_ttl_seconds,
        ),
        redis=redis,
    )


@asynccontextmanager
async def open_taxonomy_layout_service(
    runtime: TaxonomyViewLayoutRuntime,
) -> AsyncIterator[TaxonomyService]:
    async with runtime.session_factory() as session:
        knowledge_projection_port = build_knowledge_graph_service(
            session=session,
            edge_title_mention_top_k=runtime.settings.edge_title_mention_top_k,
            edge_semantic_top_k=runtime.settings.edge_semantic_top_k,
            edge_semantic_min_strength=runtime.settings.edge_semantic_min_strength,
            edge_semantic_candidate_limit=runtime.settings.edge_semantic_candidate_limit,
        )
        yield TaxonomyService(
            repo=TaxonomyRepo(session=session),
            knowledge_projection_port=knowledge_projection_port,
            view_cache=runtime.view_cache,
        )


async def process_next_leaf_layout(
    *,
    cache: TaxonomyLayoutComputeCache,
    service_factory: TaxonomyLayoutServiceFactory,
) -> bool:
    leaf_id = await cache.claim_leaf_layout_compute()
    if leaf_id is None:
        return False

    try:
        async with service_factory() as service:
            await service.build_and_cache_leaf_layout(leaf_id=leaf_id)
    except Exception:
        logger.exception(
            "taxonomy_view_layout.compute_failed",
            extra={"taxonomy_leaf_id": leaf_id},
        )
    finally:
        await cache.complete_leaf_layout_compute(leaf_id=leaf_id)
    return True


async def run_forever(runtime: TaxonomyViewLayoutRuntime) -> None:
    try:
        while True:
            processed = await process_next_leaf_layout(
                cache=runtime.view_cache,
                service_factory=lambda: open_taxonomy_layout_service(runtime),
            )
            if not processed:
                await asyncio.sleep(TAXONOMY_VIEW_LAYOUT_POLL_INTERVAL_SECONDS)
    finally:
        await runtime.redis.aclose()
        await runtime.engine.dispose()


async def _async_main() -> None:
    runtime = build_runtime()
    await run_forever(runtime)


def main() -> None:
    asyncio.run(_async_main())


if __name__ == "__main__":
    main()
