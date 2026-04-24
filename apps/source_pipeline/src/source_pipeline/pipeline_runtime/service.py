"""
Abstract: Runtime tick logic for source-pipeline queue orchestration.
Out of scope: Process bootstrap and Docker/Compose integration.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from source_pipeline.card_review.contracts import ReviewResult, export_card_review_output_schema
from source_pipeline.card_review.instruction import build_card_review_instruction
from source_pipeline.db.models import CardReviewJob, WorkflowUnit
from source_pipeline.page_to_card.contracts import (
    CardDraft,
    PageToCardResult,
    SourceUnit,
    export_page_to_card_output_schema,
)
from source_pipeline.page_to_card.instruction import build_page_to_card_instruction
from source_pipeline.pipeline_handoff.ports import ReviewHandoffPort
from source_pipeline.pipeline_runtime.job_queue_client import (
    JobQueueClient,
    NotReadyJobResult,
)


class PipelineRuntimeService:
    def __init__(
        self,
        session: AsyncSession,
        *,
        job_queue_client: JobQueueClient,
        review_handoff: ReviewHandoffPort,
    ) -> None:
        self._session = session
        self._job_queue_client = job_queue_client
        self._review_handoff = review_handoff

    async def tick(self) -> None:
        units = list(
            (await self._session.execute(select(WorkflowUnit).order_by(WorkflowUnit.id))).scalars()
        )

        for unit in units:
            if unit.page_to_card_job_id is None:
                await self._submit_page_to_card(unit)
                continue

            page_result = await self._job_queue_client.get_result(job_id=unit.page_to_card_job_id)
            if isinstance(page_result, NotReadyJobResult):
                self._raise_if_dead_letter(page_result)
                continue

            page_cards = PageToCardResult.model_validate(page_result.result_payload).cards
            review_jobs = await self._ensure_review_jobs(unit=unit, cards=page_cards)
            submitted_ordinals = await self._submit_missing_review_jobs(
                unit=unit,
                cards=page_cards,
                review_jobs=review_jobs,
            )
            await self._handoff_ready_reviews(
                unit=unit,
                cards=page_cards,
                review_jobs=review_jobs,
                skip_ordinals=submitted_ordinals,
            )

        await self._session.commit()

    async def _submit_page_to_card(self, unit: WorkflowUnit) -> None:
        source_unit = SourceUnit.model_validate(unit.payload)
        unit.page_to_card_job_id = await self._job_queue_client.create_job(
            queue_name="page_to_card",
            priority="normal",
            instruction=build_page_to_card_instruction(),
            output_schema=export_page_to_card_output_schema(),
            payload=source_unit.model_dump(mode="json"),
            metadata={"workflow_unit_id": unit.id},
        )
        await self._session.flush()

    async def _ensure_review_jobs(
        self,
        *,
        unit: WorkflowUnit,
        cards: list[CardDraft],
    ) -> list[CardReviewJob]:
        review_jobs = list(
            (
                await self._session.execute(
                    select(CardReviewJob)
                    .where(CardReviewJob.workflow_unit_id == unit.id)
                    .order_by(CardReviewJob.ordinal)
                )
            ).scalars()
        )
        existing_ordinals = {job.ordinal for job in review_jobs}

        for ordinal, _card in enumerate(cards):
            if ordinal in existing_ordinals:
                continue
            self._session.add(
                CardReviewJob(
                    workflow_unit_id=unit.id,
                    ordinal=ordinal,
                )
            )

        await self._session.flush()
        return list(
            (
                await self._session.execute(
                    select(CardReviewJob)
                    .where(CardReviewJob.workflow_unit_id == unit.id)
                    .order_by(CardReviewJob.ordinal)
                )
            ).scalars()
        )

    async def _submit_missing_review_jobs(
        self,
        *,
        unit: WorkflowUnit,
        cards: list[CardDraft],
        review_jobs: list[CardReviewJob],
    ) -> set[int]:
        submitted_ordinals: set[int] = set()

        for review_job in review_jobs:
            if review_job.ordinal >= len(cards):
                raise ValueError(
                    "Review job ordinal "
                    f"{review_job.ordinal} is out of range for workflow unit {unit.id}."
                )
            if review_job.job_queue_job_id is not None:
                continue

            card = cards[review_job.ordinal]
            review_job.job_queue_job_id = await self._job_queue_client.create_job(
                queue_name="card_review",
                priority="normal",
                instruction=build_card_review_instruction(),
                output_schema=export_card_review_output_schema(),
                payload=card.model_dump(mode="json"),
                metadata={"workflow_unit_id": unit.id, "ordinal": review_job.ordinal},
            )
            submitted_ordinals.add(review_job.ordinal)

        await self._session.flush()
        return submitted_ordinals

    async def _handoff_ready_reviews(
        self,
        *,
        unit: WorkflowUnit,
        cards: list[CardDraft],
        review_jobs: list[CardReviewJob],
        skip_ordinals: set[int],
    ) -> None:
        for review_job in review_jobs:
            if review_job.job_queue_job_id is None or review_job.handoff_done:
                continue
            if review_job.ordinal in skip_ordinals:
                continue
            if review_job.ordinal >= len(cards):
                raise ValueError(
                    "Review job ordinal "
                    f"{review_job.ordinal} is out of range for workflow unit {unit.id}."
                )

            review_result = await self._job_queue_client.get_result(
                job_id=review_job.job_queue_job_id
            )
            if isinstance(review_result, NotReadyJobResult):
                self._raise_if_dead_letter(review_result)
                continue

            await self._review_handoff.handoff(
                workflow_unit_id=unit.id,
                ordinal=review_job.ordinal,
                card=cards[review_job.ordinal],
                review=ReviewResult.model_validate(review_result.result_payload),
            )
            review_job.handoff_done = True

        await self._session.flush()

    @staticmethod
    def _raise_if_dead_letter(result: NotReadyJobResult) -> None:
        if result.state == "DEAD_LETTER":
            raise RuntimeError(
                f"Job {result.job_id} reached DEAD_LETTER before an accepted result."
            )
