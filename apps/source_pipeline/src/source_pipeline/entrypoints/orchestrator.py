"""
Abstract: Long-running orchestrator bootstrap for source-pipeline queue polling.
Out of scope: Docker/Compose wiring and downstream handoff transport implementation.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncEngine

from source_pipeline.config import Settings, load_settings
from source_pipeline.db.session import SessionFactory, build_session_factory
from source_pipeline.pipeline_handoff.knowledge_ingestion import KnowledgeIngestionHandoff
from source_pipeline.pipeline_runtime.job_queue_client import JobQueueClient
from source_pipeline.pipeline_runtime.job_queue_token import ClientCredentialsTokenProvider
from source_pipeline.pipeline_runtime.service import PipelineRuntimeService


@dataclass(slots=True, frozen=True)
class OrchestratorRuntime:
    settings: Settings
    engine: AsyncEngine
    session_factory: SessionFactory
    job_queue_client: JobQueueClient
    card_handoff: KnowledgeIngestionHandoff


def build_runtime() -> OrchestratorRuntime:
    settings = load_settings()
    engine, session_factory = build_session_factory(settings)
    return OrchestratorRuntime(
        settings=settings,
        engine=engine,
        session_factory=session_factory,
        job_queue_client=JobQueueClient(
            base_url=settings.job_queue_base_url,
            token_provider=ClientCredentialsTokenProvider(
                token_url=settings.job_queue_token_url,
                client_id=settings.job_queue_client_id,
                client_secret=settings.job_queue_client_secret,
                resource=settings.job_queue_resource,
                scope=settings.job_queue_scopes,
            ),
        ),
        card_handoff=KnowledgeIngestionHandoff(base_url=settings.knowledge_api_base_url),
    )


async def run_forever(runtime: OrchestratorRuntime) -> None:
    try:
        while True:
            async with runtime.session_factory() as session:
                service = PipelineRuntimeService(
                    session,
                    job_queue_client=runtime.job_queue_client,
                    card_handoff=runtime.card_handoff,
                )
                await service.tick()

            await asyncio.sleep(runtime.settings.poll_interval_seconds)
    finally:
        await runtime.job_queue_client.aclose()
        await runtime.card_handoff.aclose()
        await runtime.engine.dispose()


async def _async_main() -> None:
    runtime = build_runtime()
    await run_forever(runtime)


def main() -> None:
    asyncio.run(_async_main())


if __name__ == "__main__":
    main()
