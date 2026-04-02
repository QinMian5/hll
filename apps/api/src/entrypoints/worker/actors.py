"""
Abstract: Dramatiq actor entrypoint that assembles runtime dependencies and runs jobs.
Out of scope: HTTP transport behavior and module-level business orchestration rules.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import Protocol

import dramatiq

from core.logging import configure_logging, get_logger
from entrypoints.runtime import get_runtime_dependencies, get_settings


class _LoggingSettings(Protocol):
    log_level: str
    log_file_path: str
    log_file_max_bytes: int
    log_file_backup_count: int


class _ConfigureLogging(Protocol):
    def __call__(
        self,
        *,
        log_level: str,
        log_file_path: str,
        log_file_max_bytes: int,
        log_file_backup_count: int,
    ) -> None: ...


def bootstrap_worker_logging(
    *,
    settings_loader: Callable[[], _LoggingSettings] = get_settings,
    configure: _ConfigureLogging = configure_logging,
) -> _LoggingSettings:
    settings = settings_loader()
    configure(
        log_level=settings.log_level,
        log_file_path=settings.log_file_path,
        log_file_max_bytes=settings.log_file_max_bytes,
        log_file_backup_count=settings.log_file_backup_count,
    )
    return settings


bootstrap_worker_logging()
logger = get_logger(__name__)


@dramatiq.actor(queue_name="ingestion")
def enqueue_ingestion_task(
    ingestion_id: str,
    request_id: str,
    title: str,
    content: str,
) -> None:
    logger.info(
        "ingestion.worker_received",
        extra={
            "event": "ingestion.worker_received",
            "ingestion_id": ingestion_id,
            "request_id": request_id,
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
                title=title,
                content=content,
                embedding_client=runtime.embedding_client,
                knowledge_graph_write_port=knowledge_graph_service,
            )

    asyncio.run(_run())
