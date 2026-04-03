"""
Abstract: Dramatiq actor entrypoint that assembles runtime dependencies and runs jobs.
Out of scope: HTTP transport behavior and module-level business orchestration rules.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable

import dramatiq

from core.logging import configure_logging, get_logger
from entrypoints.logging_bootstrap import (
    ConfigureLogging,
    LoggingSettings,
    bootstrap_logging,
)
from entrypoints.runtime import get_runtime_dependencies, get_settings
from modules.ingestion.queue import (
    INGESTION_ACTOR_NAME,
    INGESTION_QUEUE_NAME,
    IngestionTask,
    configure_broker,
)


def bootstrap_worker_logging(
    *,
    settings_loader: Callable[[], LoggingSettings] = get_settings,
    configure: ConfigureLogging = configure_logging,
) -> LoggingSettings:
    return bootstrap_logging(
        settings_loader=settings_loader,
        configure=configure,
    )


runtime_settings = get_settings()
bootstrap_worker_logging(settings_loader=lambda: runtime_settings)
configure_broker(redis_url=runtime_settings.redis_url)
logger = get_logger(__name__)


@dramatiq.actor(
    queue_name=INGESTION_QUEUE_NAME,
    actor_name=INGESTION_ACTOR_NAME,
)
def enqueue_ingestion_task(
    task_payload: dict[str, str],
) -> None:
    task = IngestionTask.from_payload(task_payload)
    logger.info(
        "ingestion.worker_received",
        extra={
            "event": "ingestion.worker_received",
            "ingestion_id": task.ingestion_id,
            "request_id": task.request_id,
        },
    )
    runtime = get_runtime_dependencies()

    async def _run() -> int:
        from modules.ingestion.workers import process_ingestion_job
        from modules.knowledge_graph.builders import build_knowledge_graph_service

        async with runtime.session_factory() as session:
            knowledge_graph_service = build_knowledge_graph_service(
                session=session,
                edge_similarity_top_k=runtime.settings.edge_similarity_top_k,
                edge_similarity_min_strength=runtime.settings.edge_similarity_min_strength,
            )
            return await process_ingestion_job(
                title=task.title,
                content=task.content,
                embedding_client=runtime.embedding_client,
                knowledge_graph_write_port=knowledge_graph_service,
            )

    asyncio.run(_run())
