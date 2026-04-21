"""
Abstract: Long-running orchestrator bootstrap for source-pipeline queue polling.
Out of scope: Docker/Compose wiring and downstream handoff transport implementation.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncEngine

from source_pipeline.card_review.contracts import ReviewResult
from source_pipeline.config import Settings, load_settings
from source_pipeline.db.session import SessionFactory, build_session_factory
from source_pipeline.page_to_card.contracts import CardDraft
from source_pipeline.pipeline_handoff.ports import ReviewHandoffPort
from source_pipeline.pipeline_runtime.job_queue_client import JobQueueClient
from source_pipeline.pipeline_runtime.service import PipelineRuntimeService


class UnconfiguredReviewHandoff(ReviewHandoffPort):
    async def handoff(
        self,
        *,
        workflow_unit_id: int,
        ordinal: int,
        card: CardDraft,
        review: ReviewResult,
    ) -> None:
        raise RuntimeError(
            "Source-pipeline review handoff is not configured. "
            "Wire a concrete downstream handoff before processing accepted review results."
        )


@dataclass(slots=True, frozen=True)
class OrchestratorRuntime:
    settings: Settings
    engine: AsyncEngine
    session_factory: SessionFactory
    job_queue_client: JobQueueClient
    review_handoff: ReviewHandoffPort


def build_runtime() -> OrchestratorRuntime:
    settings = load_settings()
    engine, session_factory = build_session_factory(settings)
    return OrchestratorRuntime(
        settings=settings,
        engine=engine,
        session_factory=session_factory,
        job_queue_client=JobQueueClient(
            base_url=settings.job_queue_base_url,
            producer_token=settings.producer_token,
            results_reader_token=settings.results_reader_token,
        ),
        review_handoff=UnconfiguredReviewHandoff(),
    )


async def run_forever(runtime: OrchestratorRuntime) -> None:
    try:
        while True:
            async with runtime.session_factory() as session:
                service = PipelineRuntimeService(
                    session,
                    job_queue_client=runtime.job_queue_client,
                    review_handoff=runtime.review_handoff,
                )
                await service.tick()

            await asyncio.sleep(runtime.settings.poll_interval_seconds)
    finally:
        await runtime.job_queue_client.aclose()
        await runtime.engine.dispose()


async def _async_main() -> None:
    runtime = build_runtime()
    await run_forever(runtime)


def main() -> None:
    asyncio.run(_async_main())


if __name__ == "__main__":
    main()
