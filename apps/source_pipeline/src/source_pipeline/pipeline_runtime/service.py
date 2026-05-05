"""
Abstract: Runtime tick logic for source-pipeline queue orchestration.
Out of scope: Process bootstrap and Docker/Compose integration.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from datetime import UTC, datetime, timedelta
from typing import Protocol

from job_queue_mcp_client.errors import ResultNotReadyError
from job_queue_mcp_client.types import (
    AcceptedResult as AcceptedJobResult,
)
from job_queue_mcp_client.types import (
    CreatedJob,
    CreateJobItem,
)
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
from source_pipeline.db.models import CardCandidate, JobQueueWebhookEvent, WorkflowUnit
from source_pipeline.page_to_card.contracts import (
    CardDraft,
    PageToCardResult,
    SourceUnit,
    export_page_to_card_output_schema,
)
from source_pipeline.page_to_card.instruction import build_page_to_card_instruction
from source_pipeline.pipeline_handoff.ports import AcceptedCardHandoffPort
from source_pipeline.pipeline_webhook.repository import JobQueueWebhookEventRepository

TERMINAL_NON_ACCEPTED_STATES = frozenset({"CANCELLED", "DEAD_LETTER", "FAILED", "EXPIRED"})


class JobQueueClientPort(Protocol):
    async def create_jobs(self, jobs: Sequence[CreateJobItem]) -> list[CreatedJob]: ...

    async def get_result(self, job_id: int) -> AcceptedJobResult: ...


class PipelineRuntimeService:
    def __init__(
        self,
        session: AsyncSession,
        *,
        job_queue_client: JobQueueClientPort,
        card_handoff: AcceptedCardHandoffPort,
        poll_batch_size: int = 100,
        reconcile_interval_seconds: float = 3600,
        reconcile_batch_size: int = 100,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        if poll_batch_size < 1:
            raise ValueError("poll_batch_size must be at least 1")
        if reconcile_batch_size < 1:
            raise ValueError("reconcile_batch_size must be at least 1")
        if reconcile_interval_seconds <= 0:
            raise ValueError("reconcile_interval_seconds must be greater than 0")
        self._session = session
        self._job_queue_client = job_queue_client
        self._card_handoff = card_handoff
        self._poll_batch_size = poll_batch_size
        self._reconcile_interval = timedelta(seconds=reconcile_interval_seconds)
        self._reconcile_batch_size = reconcile_batch_size
        self._clock = clock or (lambda: datetime.now(UTC))
        self._last_reconcile_at: datetime | None = None

    async def tick(self) -> None:
        now = self._clock()
        submitted_count = await self._submit_missing_page_to_card_jobs()
        if submitted_count > 0:
            await self._session.commit()
            return

        processed_count = await self.process_pending_webhook_events(now=now)
        if processed_count > 0:
            await self._session.commit()
            return

        if await self.run_low_frequency_reconcile(now=now):
            await self._session.commit()

    async def process_pending_webhook_events(self, *, now: datetime) -> int:
        repository = JobQueueWebhookEventRepository(self._session)
        events = await repository.list_pending_events(limit=self._poll_batch_size)

        for event in events:
            try:
                await self._process_webhook_event(event)
                await repository.mark_processed(event_id=event.event_id, processed_at=now)
            except Exception as exc:
                await repository.mark_failed(
                    event_id=event.event_id,
                    last_error=str(exc),
                    failed_at=now,
                )

        return len(events)

    async def run_low_frequency_reconcile(self, *, now: datetime) -> bool:
        if self._last_reconcile_at is None:
            self._last_reconcile_at = now
            return False
        if now - self._last_reconcile_at < self._reconcile_interval:
            return False

        self._last_reconcile_at = now
        units = list(
            (
                await self._session.execute(
                    select(WorkflowUnit)
                    .where(WorkflowUnit.page_to_card_job_id.is_not(None))
                    .where(WorkflowUnit.page_to_card_terminal_state.is_(None))
                    .order_by(WorkflowUnit.id)
                    .limit(self._reconcile_batch_size)
                )
            ).scalars()
        )

        for unit in units:
            try:
                page_result = await self._job_queue_client.get_result(
                    self._require_job_id(unit.page_to_card_job_id)
                )
            except ResultNotReadyError as exc:
                if _terminal_non_accepted_state(exc.state):
                    unit.page_to_card_terminal_state = exc.state
                continue

            await self._ensure_initial_candidates(unit=unit, page_result=page_result)
            await self._advance_candidates(unit=unit)

        return bool(units)

    async def _process_webhook_event(self, event: JobQueueWebhookEvent) -> None:
        if event.event_type == "result.accepted":
            await self._process_accepted_job_result(job_id=event.job_id)
            return
        if event.event_type == "job.terminal_non_accepted":
            await self._process_terminal_non_accepted_job(
                job_id=event.job_id,
                terminal_state=self._require_terminal_state(event.terminal_state),
            )
            return
        raise ValueError(f"Unsupported webhook event type: {event.event_type}")

    async def _process_accepted_job_result(self, *, job_id: int) -> None:
        unit = await self._unit_for_page_job(job_id=job_id)
        if unit is not None:
            page_result = await self._accepted_result(job_id=job_id)
            await self._ensure_initial_candidates(unit=unit, page_result=page_result)
            await self._submit_missing_review_jobs(unit=unit)
            return

        review_candidate = await self._candidate_for_review_job(job_id=job_id)
        if review_candidate is not None:
            review_result = await self._accepted_result(job_id=job_id)
            await self._process_review_result(
                candidate=review_candidate,
                review_result=review_result,
            )
            return

        repair_candidate = await self._candidate_for_repair_job(job_id=job_id)
        if repair_candidate is not None:
            repair_result = await self._accepted_result(job_id=job_id)
            await self._ensure_child_candidates(
                candidate=repair_candidate,
                repair_result=repair_result,
            )
            unit = await self._session.get(WorkflowUnit, repair_candidate.workflow_unit_id)
            if unit is not None:
                await self._submit_missing_review_jobs(unit=unit)
            return

    async def _process_terminal_non_accepted_job(
        self,
        *,
        job_id: int,
        terminal_state: str,
    ) -> None:
        unit = await self._unit_for_page_job(job_id=job_id)
        if unit is not None:
            unit.page_to_card_terminal_state = terminal_state
            await self._session.flush()
            return

        review_candidate = await self._candidate_for_review_job(job_id=job_id)
        if review_candidate is not None:
            review_candidate.review_terminal_state = terminal_state
            await self._session.flush()
            return

        repair_candidate = await self._candidate_for_repair_job(job_id=job_id)
        if repair_candidate is not None:
            repair_candidate.repair_terminal_state = terminal_state
            await self._session.flush()
            return

    async def _accepted_result(self, *, job_id: int) -> AcceptedJobResult:
        try:
            return await self._job_queue_client.get_result(job_id)
        except ResultNotReadyError as exc:
            raise ValueError(
                f"Webhook indicated accepted result but job {job_id} is not ready."
            ) from exc

    async def _unit_for_page_job(self, *, job_id: int) -> WorkflowUnit | None:
        return await self._session.scalar(
            select(WorkflowUnit).where(WorkflowUnit.page_to_card_job_id == job_id).limit(1)
        )

    async def _candidate_for_review_job(self, *, job_id: int) -> CardCandidate | None:
        return await self._session.scalar(
            select(CardCandidate).where(CardCandidate.review_job_id == job_id).limit(1)
        )

    async def _candidate_for_repair_job(self, *, job_id: int) -> CardCandidate | None:
        return await self._session.scalar(
            select(CardCandidate).where(CardCandidate.repair_job_id == job_id).limit(1)
        )

    async def _submit_missing_review_jobs(self, *, unit: WorkflowUnit) -> None:
        candidates = await self._list_candidates_for_unit(unit_id=unit.id)
        for candidate in candidates:
            if candidate.review_job_id is None:
                await self._submit_review_job(candidate)

    async def _process_review_result(
        self,
        *,
        candidate: CardCandidate,
        review_result: AcceptedJobResult,
    ) -> None:
        review = ReviewResult.model_validate(review_result.result_payload)
        if _review_passed(review):
            await self._handoff_passed_candidate(candidate)
            return

        if candidate.repair_job_id is None:
            await self._submit_repair_job(candidate=candidate, review=review)

    async def _submit_missing_page_to_card_jobs(self) -> int:
        units = list(
            (
                await self._session.execute(
                    select(WorkflowUnit)
                    .where(WorkflowUnit.page_to_card_job_id.is_(None))
                    .where(WorkflowUnit.page_to_card_terminal_state.is_(None))
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
        unit.page_to_card_job_id = await self._create_idempotent_job(
            queue_name="page_to_card",
            idempotency_key=f"source-pipeline:page-to-card:workflow-unit:{unit.id}",
            priority="normal",
            instruction=build_page_to_card_instruction(),
            output_schema=export_page_to_card_output_schema(),
            payload=source_unit.model_dump(mode="json"),
            metadata={"workflow_unit_id": unit.id},
        )
        await self._session.flush()

    async def _create_idempotent_job(
        self,
        *,
        queue_name: str,
        idempotency_key: str,
        instruction: str,
        output_schema: dict[str, object],
        priority: str = "normal",
        payload: dict[str, object] | None = None,
        metadata: dict[str, object] | None = None,
    ) -> int:
        created_jobs = await self._job_queue_client.create_jobs(
            [
                CreateJobItem(
                    queue_name=queue_name,
                    idempotency_key=idempotency_key,
                    priority=priority,
                    instruction=instruction,
                    output_schema=output_schema,
                    payload=payload or {},
                    metadata=metadata or {},
                )
            ]
        )
        if len(created_jobs) != 1 or created_jobs[0].index != 0:
            raise RuntimeError("Expected exactly one idempotent job creation result.")
        return created_jobs[0].job_id

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

            if candidate.review_terminal_state is not None:
                continue

            try:
                review_result = await self._job_queue_client.get_result(candidate.review_job_id)
            except ResultNotReadyError as exc:
                if _terminal_non_accepted_state(exc.state):
                    candidate.review_terminal_state = exc.state
                continue

            review = ReviewResult.model_validate(review_result.result_payload)
            if _review_passed(review):
                await self._handoff_passed_candidate(candidate)
                continue

            if candidate.repair_job_id is None:
                await self._submit_repair_job(candidate=candidate, review=review)
                continue

            if candidate.repair_terminal_state is not None:
                continue

            try:
                repair_result = await self._job_queue_client.get_result(candidate.repair_job_id)
            except ResultNotReadyError as exc:
                if _terminal_non_accepted_state(exc.state):
                    candidate.repair_terminal_state = exc.state
                continue

            await self._ensure_child_candidates(candidate=candidate, repair_result=repair_result)

        await self._session.flush()

    async def _submit_review_job(self, candidate: CardCandidate) -> None:
        card = CardDraft.model_validate(candidate.card_payload)
        candidate.review_job_id = await self._create_idempotent_job(
            queue_name="card_review",
            idempotency_key=f"source-pipeline:card-review:candidate:{candidate.id}",
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
        candidate.repair_job_id = await self._create_idempotent_job(
            queue_name="card_repair",
            idempotency_key=f"source-pipeline:card-repair:candidate:{candidate.id}",
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

    @staticmethod
    def _require_terminal_state(terminal_state: str | None) -> str:
        if terminal_state is None:
            raise RuntimeError("Expected source-pipeline webhook terminal state to be present.")
        return terminal_state


def _review_passed(review: ReviewResult) -> bool:
    return review.passed


def _terminal_non_accepted_state(state: str | None) -> bool:
    return state in TERMINAL_NON_ACCEPTED_STATES
