"""
Abstract: Dramatiq actor entrypoint that assembles runtime dependencies and runs jobs.
Out of scope: HTTP transport behavior and module-level business orchestration rules.
"""

from __future__ import annotations

import asyncio

import dramatiq

from core.logging import get_logger
from entrypoints.runtime import get_runtime_dependencies
from modules.ingestion.queue import (
    INGESTION_ACTOR_NAME,
    INGESTION_QUEUE_NAME,
    IngestionTask,
)

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
