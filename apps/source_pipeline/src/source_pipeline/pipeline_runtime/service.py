"""
Abstract: Runtime tick logic for source-pipeline queue orchestration.
Out of scope: Process bootstrap and Docker/Compose integration.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from source_pipeline.card_repair.contracts import (
    CardRepairInput,
    CardRepairResult,
    export_card_repair_output_schema,
)
from source_pipeline.card_repair.instruction import build_card_repair_instruction
from source_pipeline.card_review.contracts import ReviewResult, export_card_review_output_schema
from source_pipeline.card_review.instruction import build_card_review_instruction
from source_pipeline.db.models import CardCandidate, WorkflowUnit
from source_pipeline.page_to_card.contracts import (
    CardDraft,
    PageToCardResult,
    SourceUnit,
    export_page_to_card_output_schema,
)
from source_pipeline.page_to_card.instruction import build_page_to_card_instruction
from source_pipeline.pipeline_handoff.ports import AcceptedCardHandoffPort
from source_pipeline.pipeline_runtime.job_queue_client import (
    AcceptedJobResult,
    JobQueueClient,
    NotReadyJobResult,
)

TERMINAL_NON_ACCEPTED_STATES = frozenset({"CANCELLED", "DEAD_LETTER", "FAILED", "EXPIRED"})


class PipelineRuntimeService:
    def __init__(
        self,
        session: AsyncSession,
        *,
        job_queue_client: JobQueueClient,
        card_handoff: AcceptedCardHandoffPort,
        poll_batch_size: int = 100,
    ) -> None:
        if poll_batch_size < 1:
            raise ValueError("poll_batch_size must be at least 1")
        self._session = session
        self._job_queue_client = job_queue_client
        self._card_handoff = card_handoff
        self._poll_batch_size = poll_batch_size

    async def tick(self) -> None:
        submitted_count = await self._submit_missing_page_to_card_jobs()
        if submitted_count > 0:
            await self._session.commit()
            return

        units = list(
            (
                await self._session.execute(
                    select(WorkflowUnit)
                    .where(WorkflowUnit.page_to_card_job_id.is_not(None))
                    .order_by(WorkflowUnit.id)
                )
            ).scalars()
        )

        for unit in units:
            page_result = await self._job_queue_client.get_result(
                job_id=self._require_job_id(unit.page_to_card_job_id)
            )
            if isinstance(page_result, NotReadyJobResult):
                continue

            await self._ensure_initial_candidates(unit=unit, page_result=page_result)
            await self._advance_candidates(unit=unit)

        await self._session.commit()

    async def _submit_missing_page_to_card_jobs(self) -> int:
        units = list(
            (
                await self._session.execute(
                    select(WorkflowUnit)
                    .where(WorkflowUnit.page_to_card_job_id.is_(None))
                    .order_by(WorkflowUnit.id)
                    .limit(self._poll_batch_size)
                )
            ).scalars()
        )
        for unit in units:
            await self._submit_page_to_card(unit)
        return len(units)

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

    async def _ensure_initial_candidates(
        self,
        *,
        unit: WorkflowUnit,
        page_result: AcceptedJobResult,
    ) -> None:
        cards = PageToCardResult.model_validate(page_result.result_payload).cards
        existing_origins = await self._candidate_origins_for_unit(unit_id=unit.id)
        page_job_id = self._require_job_id(unit.page_to_card_job_id)

        for ordinal, card in enumerate(cards):
            origin = ("page_to_card", page_job_id, ordinal)
            if origin in existing_origins:
                continue
            self._session.add(
                CardCandidate(
                    workflow_unit_id=unit.id,
                    card_payload=card.model_dump(mode="json"),
                    origin_step=origin[0],
                    origin_job_id=origin[1],
                    origin_ordinal=origin[2],
                )
            )

        await self._session.flush()

    async def _advance_candidates(self, *, unit: WorkflowUnit) -> None:
        candidates = await self._list_candidates_for_unit(unit_id=unit.id)

        for candidate in candidates:
            if candidate.review_job_id is None:
                await self._submit_review_job(candidate)
                continue

            review_result = await self._job_queue_client.get_result(job_id=candidate.review_job_id)
            if isinstance(review_result, NotReadyJobResult):
                continue

            review = ReviewResult.model_validate(review_result.result_payload)
            if _review_passed(review):
                await self._handoff_passed_candidate(candidate)
                continue

            if candidate.repair_job_id is None:
                await self._submit_repair_job(candidate=candidate, review=review)
                continue

            repair_result = await self._job_queue_client.get_result(job_id=candidate.repair_job_id)
            if isinstance(repair_result, NotReadyJobResult):
                continue

            await self._ensure_child_candidates(candidate=candidate, repair_result=repair_result)

        await self._session.flush()

    async def _submit_review_job(self, candidate: CardCandidate) -> None:
        card = CardDraft.model_validate(candidate.card_payload)
        candidate.review_job_id = await self._job_queue_client.create_job(
            queue_name="card_review",
            priority="normal",
            instruction=build_card_review_instruction(),
            output_schema=export_card_review_output_schema(),
            payload=card.model_dump(mode="json"),
            metadata={
                "workflow_unit_id": candidate.workflow_unit_id,
                "candidate_id": candidate.id,
            },
        )
        await self._session.flush()

    async def _handoff_passed_candidate(self, candidate: CardCandidate) -> None:
        if candidate.ingestion_handoff_done:
            return

        await self._card_handoff.handoff(
            candidate_id=candidate.id,
            card=CardDraft.model_validate(candidate.card_payload),
        )
        candidate.ingestion_handoff_done = True
        await self._session.flush()

    async def _submit_repair_job(
        self,
        *,
        candidate: CardCandidate,
        review: ReviewResult,
    ) -> None:
        card = CardDraft.model_validate(candidate.card_payload)
        repair_input = CardRepairInput(card=card, review=review)
        candidate.repair_job_id = await self._job_queue_client.create_job(
            queue_name="card_repair",
            priority="normal",
            instruction=build_card_repair_instruction(),
            output_schema=export_card_repair_output_schema(),
            payload=repair_input.model_dump(mode="json"),
            metadata={
                "workflow_unit_id": candidate.workflow_unit_id,
                "candidate_id": candidate.id,
            },
        )
        await self._session.flush()

    async def _ensure_child_candidates(
        self,
        *,
        candidate: CardCandidate,
        repair_result: AcceptedJobResult,
    ) -> None:
        result = CardRepairResult.model_validate(repair_result.result_payload)
        existing_origins = await self._candidate_origins_for_parent(
            parent_candidate_id=candidate.id
        )
        repair_job_id = self._require_job_id(candidate.repair_job_id)

        for ordinal, card in enumerate(result.cards):
            origin = ("card_repair", repair_job_id, ordinal)
            if origin in existing_origins:
                continue
            self._session.add(
                CardCandidate(
                    workflow_unit_id=candidate.workflow_unit_id,
                    parent_candidate_id=candidate.id,
                    card_payload=card.model_dump(mode="json"),
                    origin_step=origin[0],
                    origin_job_id=origin[1],
                    origin_ordinal=origin[2],
                )
            )

        await self._session.flush()

    async def _list_candidates_for_unit(self, *, unit_id: int) -> list[CardCandidate]:
        return list(
            (
                await self._session.execute(
                    select(CardCandidate)
                    .where(CardCandidate.workflow_unit_id == unit_id)
                    .order_by(CardCandidate.id)
                )
            ).scalars()
        )

    async def _candidate_origins_for_unit(self, *, unit_id: int) -> set[tuple[str, int, int]]:
        candidates = await self._list_candidates_for_unit(unit_id=unit_id)
        return {
            (candidate.origin_step, candidate.origin_job_id, candidate.origin_ordinal)
            for candidate in candidates
        }

    async def _candidate_origins_for_parent(
        self,
        *,
        parent_candidate_id: int,
    ) -> set[tuple[str, int, int]]:
        candidates = list(
            (
                await self._session.execute(
                    select(CardCandidate).where(
                        CardCandidate.parent_candidate_id == parent_candidate_id
                    )
                )
            ).scalars()
        )
        return {
            (candidate.origin_step, candidate.origin_job_id, candidate.origin_ordinal)
            for candidate in candidates
        }

    @staticmethod
    def _require_job_id(job_id: int | None) -> int:
        if job_id is None:
            raise RuntimeError("Expected source-pipeline job id to be present.")
        return job_id


def _review_passed(review: ReviewResult) -> bool:
    return all(
        (
            review.title_validity.passed,
            review.title_content_alignment.passed,
            review.title_style_validity.passed,
            review.content_coherence.passed,
            review.content_atomicity.passed,
            review.content_latex_validity.passed,
        )
    )
