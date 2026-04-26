"""
Abstract: Runtime processing for taxonomy-classification webhook events and reconcile.
Out of scope: HTTP webhook authentication and operator command-line UX.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from modules.knowledge_graph.repo import KnowledgeRepo
from modules.taxonomy.model import NodeTaxonomyAssignment, TaxonomyNode
from modules.taxonomy.repo import UNCLASSIFIED_NODE_NAME, TaxonomyRepo
from modules.taxonomy_classification.contracts import TaxonomyClassificationAcceptedResult
from modules.taxonomy_classification.job_queue_client import (
    AcceptedTaxonomyClassificationJobResult,
    NotReadyTaxonomyClassificationJobResult,
    TaxonomyClassificationJobResult,
)
from modules.taxonomy_classification.model import (
    TaxonomyClassificationJob,
    TaxonomyClassificationWebhookEvent,
)
from modules.taxonomy_classification.webhook import TaxonomyClassificationWebhookRepository

TERMINAL_NON_ACCEPTED_STATES = frozenset({"CANCELLED", "DEAD_LETTER", "FAILED", "EXPIRED"})


class TaxonomyClassificationJobQueueClientPort(Protocol):
    async def get_result(self, *, job_id: int) -> TaxonomyClassificationJobResult: ...


class TaxonomyClassificationRuntimeService:
    def __init__(
        self,
        session: AsyncSession,
        *,
        job_queue_client: TaxonomyClassificationJobQueueClientPort,
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
        self._poll_batch_size = poll_batch_size
        self._reconcile_interval = timedelta(seconds=reconcile_interval_seconds)
        self._reconcile_batch_size = reconcile_batch_size
        self._clock = clock or (lambda: datetime.now(UTC))
        self._last_reconcile_at: datetime | None = None

    async def tick(self) -> None:
        now = self._clock()
        processed_count = await self.process_pending_webhook_events(now=now)
        if processed_count > 0:
            await self._session.commit()
            return
        if await self.run_low_frequency_reconcile(now=now):
            await self._session.commit()

    async def process_pending_webhook_events(self, *, now: datetime) -> int:
        repository = TaxonomyClassificationWebhookRepository(self._session)
        events = await repository.list_pending_events(limit=self._poll_batch_size)

        for event in events:
            try:
                await self._process_webhook_event(event, now=now)
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
        jobs = list(
            (
                await self._session.execute(
                    select(TaxonomyClassificationJob)
                    .where(TaxonomyClassificationJob.processed_at.is_(None))
                    .where(TaxonomyClassificationJob.terminal_state.is_(None))
                    .where(TaxonomyClassificationJob.job_id.is_not(None))
                    .order_by(TaxonomyClassificationJob.id.asc())
                    .limit(self._reconcile_batch_size)
                    .with_for_update(skip_locked=True)
                )
            ).scalars()
        )

        for job in jobs:
            if job.job_id is None:
                continue
            result = await self._job_queue_client.get_result(job_id=job.job_id)
            if isinstance(result, NotReadyTaxonomyClassificationJobResult):
                if result.state in TERMINAL_NON_ACCEPTED_STATES:
                    self._mark_job_terminal(job=job, terminal_state=result.state, now=now)
                continue
            await self._process_accepted_result(job=job, result=result, now=now)

        await self._session.flush()
        return bool(jobs)

    async def _process_webhook_event(
        self,
        event: TaxonomyClassificationWebhookEvent,
        *,
        now: datetime,
    ) -> None:
        job = await self._job_for_update(job_id=event.job_id)
        if event.event_type == "result.accepted":
            result = await self._accepted_result(job_id=event.job_id)
            await self._process_accepted_result(job=job, result=result, now=now)
            return
        if event.event_type == "job.terminal_non_accepted":
            self._mark_job_terminal(
                job=job,
                terminal_state=self._require_terminal_state(event.terminal_state),
                now=now,
            )
            return
        raise ValueError(f"Unsupported webhook event type: {event.event_type}")

    async def _accepted_result(self, *, job_id: int) -> AcceptedTaxonomyClassificationJobResult:
        result = await self._job_queue_client.get_result(job_id=job_id)
        if isinstance(result, NotReadyTaxonomyClassificationJobResult):
            raise ValueError(f"Webhook indicated accepted result but job {job_id} is not ready.")
        return result

    async def _process_accepted_result(
        self,
        *,
        job: TaxonomyClassificationJob,
        result: AcceptedTaxonomyClassificationJobResult,
        now: datetime,
    ) -> None:
        if job.processed_at is not None:
            return
        try:
            accepted = TaxonomyClassificationAcceptedResult.model_validate(result.result_payload)
            target_leaf_id = await self._resolve_target_leaf_id(job=job, accepted=accepted)
            await self._move_assignment_if_needed(
                node_id=job.node_id,
                source_leaf_id=job.source_unclassified_node_id,
                target_leaf_id=target_leaf_id,
            )
        except ValueError as exc:
            self._mark_job_processed_error(job=job, error=str(exc), now=now)
            return

        job.processed_at = now
        job.target_payload = accepted.model_dump(mode="json")
        job.last_error = None
        job.updated_at = now
        await self._session.flush()

    async def _resolve_target_leaf_id(
        self,
        *,
        job: TaxonomyClassificationJob,
        accepted: TaxonomyClassificationAcceptedResult,
    ) -> int:
        if accepted.target.kind == "unclassified":
            return job.source_unclassified_node_id

        child_id = accepted.target.child_id
        if child_id is None:
            raise ValueError("child target is missing child_id")
        child = await self._session.get(TaxonomyNode, child_id)
        if child is None or child.parent_id != job.scope_node_id:
            raise ValueError("out-of-scope child target")
        if child.is_leaf:
            raise ValueError("child target must be a regular taxonomy node")

        target_leaf = await self._session.scalar(
            select(TaxonomyNode)
            .where(TaxonomyNode.parent_id == child.id)
            .where(TaxonomyNode.name == UNCLASSIFIED_NODE_NAME)
            .where(TaxonomyNode.is_leaf.is_(True))
            .limit(1)
        )
        if target_leaf is None:
            raise ValueError("target child is missing an Unclassified leaf")
        return target_leaf.id

    async def _move_assignment_if_needed(
        self,
        *,
        node_id: int,
        source_leaf_id: int,
        target_leaf_id: int,
    ) -> None:
        assignment = await self._session.scalar(
            select(NodeTaxonomyAssignment)
            .where(NodeTaxonomyAssignment.node_id == node_id)
            .limit(1)
            .with_for_update()
        )
        if assignment is None:
            raise ValueError("card assignment is missing")
        if assignment.taxonomy_node_id != source_leaf_id:
            raise ValueError("card assignment no longer belongs to source Unclassified leaf")
        if assignment.taxonomy_node_id == target_leaf_id:
            return

        source_leaf_id_before_move = assignment.taxonomy_node_id
        await TaxonomyRepo(session=self._session).set_current_assignment(
            node_id=node_id,
            taxonomy_node_id=target_leaf_id,
        )
        for leaf_id in sorted({source_leaf_id_before_move, target_leaf_id}):
            await self._refresh_leaf_projection(leaf_id=leaf_id)

    async def _refresh_leaf_projection(self, *, leaf_id: int) -> None:
        taxonomy_repo = TaxonomyRepo(session=self._session)
        knowledge_repo = KnowledgeRepo(session=self._session)
        inner_node_ids = await taxonomy_repo.list_assigned_node_ids_for_leaf(leaf_id=leaf_id)
        adjacent_edge_ids = await knowledge_repo.fetch_adjacent_edge_ids_for_node_ids(
            node_ids=inner_node_ids
        )
        await taxonomy_repo.clear_projected_edge_ids_for_leaf(leaf_id=leaf_id)
        await taxonomy_repo.add_projected_edge_ids_for_leaf(
            leaf_id=leaf_id,
            edge_ids=adjacent_edge_ids,
        )

    async def _job_for_update(self, *, job_id: int) -> TaxonomyClassificationJob:
        job = await self._session.scalar(
            select(TaxonomyClassificationJob)
            .where(TaxonomyClassificationJob.job_id == job_id)
            .limit(1)
            .with_for_update()
        )
        if job is None:
            raise ValueError(f"Taxonomy-classification job {job_id} does not exist.")
        return job

    def _mark_job_terminal(
        self,
        *,
        job: TaxonomyClassificationJob,
        terminal_state: str,
        now: datetime,
    ) -> None:
        job.terminal_state = terminal_state
        job.updated_at = now

    def _mark_job_processed_error(
        self,
        *,
        job: TaxonomyClassificationJob,
        error: str,
        now: datetime,
    ) -> None:
        job.processed_at = now
        job.last_error = error
        job.updated_at = now

    @staticmethod
    def _require_terminal_state(terminal_state: str | None) -> str:
        if terminal_state in (None, ""):
            raise RuntimeError("Expected taxonomy-classification terminal state to be present.")
        return terminal_state


__all__ = ["TaxonomyClassificationRuntimeService"]
