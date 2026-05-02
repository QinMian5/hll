"""
Abstract: Runtime processing for taxonomy-classification webhook events and reconcile.
Out of scope: HTTP webhook authentication and operator command-line UX.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Protocol

from job_queue_mcp_client.errors import JobQueueMCPClientError
from job_queue_mcp_client.types import AcceptedResult as AcceptedTaxonomyClassificationJobResult
from job_queue_mcp_client.types import CreatedJob, CreateJobItem, ResultReadItem
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from modules.knowledge_graph.model import Node
from modules.knowledge_graph.repo import KnowledgeRepo
from modules.taxonomy.dto import TaxonomyScopeIdentity
from modules.taxonomy.model import NodeTaxonomyAssignment, TaxonomyNode
from modules.taxonomy.repo import UNCLASSIFIED_NODE_NAME, TaxonomyRepo
from modules.taxonomy_classification.contracts import TaxonomyClassificationAcceptedResult
from modules.taxonomy_classification.model import (
    TaxonomyClassificationContinuationRequest,
    TaxonomyClassificationJob,
    TaxonomyClassificationProjectionRefreshRequest,
    TaxonomyClassificationWebhookEvent,
)
from modules.taxonomy_classification.scope_resolution import (
    TaxonomyClassificationScopeResolutionError,
    resolve_taxonomy_classification_scope_by_node_id,
)
from modules.taxonomy_classification.submission import (
    MAX_JOB_QUEUE_BATCH_SIZE,
    TaxonomyClassificationExistingJobSubmission,
    TaxonomyClassificationSubmissionService,
)
from modules.taxonomy_classification.webhook import TaxonomyClassificationWebhookRepository

TERMINAL_NON_ACCEPTED_STATES = frozenset({"CANCELLED", "DEAD_LETTER", "FAILED", "EXPIRED"})
MAX_RESULT_READ_BATCH_SIZE = 1000


class TaxonomyClassificationJobQueueClientPort(Protocol):
    async def get_results(self, job_ids: Sequence[int]) -> Sequence[ResultReadItem]: ...
    async def create_jobs(self, jobs: Sequence[CreateJobItem]) -> Sequence[CreatedJob]: ...


@dataclass(frozen=True, slots=True)
class _PreparedContinuationSubmission:
    request_id: int
    submission: TaxonomyClassificationExistingJobSubmission


class TaxonomyClassificationRuntimeService:
    def __init__(
        self,
        session: AsyncSession,
        *,
        job_queue_client: TaxonomyClassificationJobQueueClientPort,
        queue_name: str | None = None,
        poll_batch_size: int = 100,
        reconcile_interval_seconds: float = 3600,
        reconcile_batch_size: int = 100,
        continuation_request_batch_size: int = MAX_JOB_QUEUE_BATCH_SIZE,
        continuation_flush_interval_seconds: float = 60,
        projection_refresh_batch_size: int = 1,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        if poll_batch_size < 1:
            raise ValueError("poll_batch_size must be at least 1")
        if reconcile_batch_size < 1:
            raise ValueError("reconcile_batch_size must be at least 1")
        if continuation_request_batch_size < 1:
            raise ValueError("continuation_request_batch_size must be at least 1")
        if continuation_request_batch_size > MAX_JOB_QUEUE_BATCH_SIZE:
            raise ValueError("continuation_request_batch_size must be at most 1000")
        if projection_refresh_batch_size < 1:
            raise ValueError("projection_refresh_batch_size must be at least 1")
        if reconcile_interval_seconds <= 0:
            raise ValueError("reconcile_interval_seconds must be greater than 0")
        if continuation_flush_interval_seconds <= 0:
            raise ValueError("continuation_flush_interval_seconds must be greater than 0")
        if queue_name == "":
            raise ValueError("queue_name must not be empty")
        self._session = session
        self._job_queue_client = job_queue_client
        self._queue_name = queue_name
        self._poll_batch_size = poll_batch_size
        self._reconcile_interval = timedelta(seconds=reconcile_interval_seconds)
        self._reconcile_batch_size = reconcile_batch_size
        self._continuation_request_batch_size = continuation_request_batch_size
        self._continuation_flush_interval = timedelta(seconds=continuation_flush_interval_seconds)
        self._projection_refresh_batch_size = projection_refresh_batch_size
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
            return
        if await self.drain_continuation_requests(now=now) > 0:
            await self._session.commit()
            return
        if await self.drain_projection_refresh_requests(now=now) > 0:
            await self._session.commit()

    async def process_pending_webhook_events(self, *, now: datetime) -> int:
        repository = TaxonomyClassificationWebhookRepository(self._session)
        events = await repository.list_pending_events(limit=self._poll_batch_size)
        accepted_events = [event for event in events if event.event_type == "result.accepted"]
        failed_event_ids: set[str] = set()
        accepted_results_by_job_id: dict[int, ResultReadItem] = {}
        if accepted_events:
            try:
                accepted_results_by_job_id = await self._result_items_by_job_id(
                    [event.job_id for event in accepted_events]
                )
            except Exception as exc:
                for event in accepted_events:
                    await repository.mark_failed(
                        event_id=event.event_id,
                        last_error=str(exc),
                        failed_at=now,
                    )
                    failed_event_ids.add(event.event_id)

        for event in events:
            if event.event_id in failed_event_ids:
                continue
            try:
                await self._process_webhook_event(
                    event,
                    now=now,
                    accepted_results_by_job_id=accepted_results_by_job_id,
                )
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

        result_items_by_job_id = await self._result_items_by_job_id(
            [job.job_id for job in jobs if job.job_id is not None]
        )

        for job in jobs:
            if job.job_id is None:
                continue
            item = result_items_by_job_id[job.job_id]
            if item.status == "ready":
                await self._process_accepted_result(
                    job=job,
                    result=_accepted_result_from_item(item),
                    now=now,
                )
                continue
            if item.status == "not_ready":
                if item.state in TERMINAL_NON_ACCEPTED_STATES:
                    self._mark_job_terminal(job=job, terminal_state=item.state, now=now)
                continue
            if item.status == "not_found":
                job.last_error = f"Remote taxonomy-classification job {job.job_id} was not found."
                job.updated_at = now
                continue
            raise ValueError(f"Unsupported result read status: {item.status}")

        await self._session.flush()
        return bool(jobs)

    async def _process_webhook_event(
        self,
        event: TaxonomyClassificationWebhookEvent,
        *,
        now: datetime,
        accepted_results_by_job_id: Mapping[int, ResultReadItem],
    ) -> None:
        job = await self._job_for_update(job_id=event.job_id)
        if event.event_type == "result.accepted":
            result = _accepted_result_from_item(
                self._require_ready_result_item(
                    job_id=event.job_id,
                    result_items_by_job_id=accepted_results_by_job_id,
                )
            )
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

    async def _result_items_by_job_id(
        self,
        job_ids: Sequence[int],
    ) -> dict[int, ResultReadItem]:
        unique_job_ids = list(dict.fromkeys(job_ids))
        result_items_by_job_id: dict[int, ResultReadItem] = {}
        for batch in _chunks(unique_job_ids, MAX_RESULT_READ_BATCH_SIZE):
            result_items = await self._job_queue_client.get_results(batch)
            _validate_result_items(result_items=result_items, requested_job_ids=batch)
            result_items_by_job_id.update({item.job_id: item for item in result_items})
        return result_items_by_job_id

    @staticmethod
    def _require_ready_result_item(
        *,
        job_id: int,
        result_items_by_job_id: Mapping[int, ResultReadItem],
    ) -> ResultReadItem:
        item = result_items_by_job_id[job_id]
        if item.status != "ready":
            raise ValueError(f"Webhook indicated accepted result but job {job_id} is not ready.")
        return item

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
            target_taxonomy_node_id = await self._resolve_target_taxonomy_node_id(
                job=job,
                accepted=accepted,
            )
            await self._move_assignment_if_needed(
                node_id=job.node_id,
                source_job_id=job.id,
                source_taxonomy_node_id=job.scope_node_id,
                target_taxonomy_node_id=target_taxonomy_node_id,
                now=now,
            )
        except ValueError as exc:
            self._mark_job_processed_error(job=job, error=str(exc), now=now)
            return

        job.processed_at = now
        job.target_payload = accepted.model_dump(mode="json")
        job.last_error = None
        job.updated_at = now
        await self._session.flush()

    async def _resolve_target_taxonomy_node_id(
        self,
        *,
        job: TaxonomyClassificationJob,
        accepted: TaxonomyClassificationAcceptedResult,
    ) -> int:
        target_name = accepted.target_name.strip()
        if target_name.casefold() == UNCLASSIFIED_NODE_NAME.casefold():
            return job.scope_node_id

        child = await self._session.scalar(
            select(TaxonomyNode)
            .where(TaxonomyNode.parent_id == job.scope_node_id)
            .where(func.lower(TaxonomyNode.name) == target_name.lower())
            .limit(1)
        )
        if child is None:
            raise ValueError("unknown child target")
        return child.id

    async def _move_assignment_if_needed(
        self,
        *,
        node_id: int,
        source_job_id: int,
        source_taxonomy_node_id: int,
        target_taxonomy_node_id: int,
        now: datetime,
    ) -> None:
        assignment = await self._session.scalar(
            select(NodeTaxonomyAssignment)
            .where(NodeTaxonomyAssignment.node_id == node_id)
            .limit(1)
            .with_for_update()
        )
        if assignment is None:
            raise ValueError("card assignment is missing")
        if assignment.taxonomy_node_id != source_taxonomy_node_id:
            raise ValueError("card assignment no longer belongs to source taxonomy scope")
        taxonomy_repo = TaxonomyRepo(session=self._session)
        previous_scope_identities = await taxonomy_repo.list_scope_identities_for_node_ids(
            node_ids=[node_id]
        )
        if assignment.taxonomy_node_id == target_taxonomy_node_id:
            await self._record_projection_refresh_requests(
                scope_identities=tuple(previous_scope_identities.values()),
                now=now,
            )
            return

        await taxonomy_repo.set_current_assignment(
            node_id=node_id,
            taxonomy_node_id=target_taxonomy_node_id,
        )
        current_scope_identities = await taxonomy_repo.list_scope_identities_for_node_ids(
            node_ids=[node_id]
        )
        await self._record_projection_refresh_requests(
            scope_identities=(
                *previous_scope_identities.values(),
                *current_scope_identities.values(),
            ),
            now=now,
        )
        await self._record_continuation_request(
            scope_node_id=target_taxonomy_node_id,
            node_id=node_id,
            source_job_id=source_job_id,
            now=now,
        )

    async def _record_continuation_request(
        self,
        *,
        scope_node_id: int,
        node_id: int,
        source_job_id: int,
        now: datetime,
    ) -> None:
        statement = pg_insert(TaxonomyClassificationContinuationRequest).values(
            scope_node_id=scope_node_id,
            node_id=node_id,
            source_job_id=source_job_id,
            next_job_id=None,
            last_error=None,
            created_at=now,
            updated_at=now,
        )
        statement = statement.on_conflict_do_update(
            index_elements=[
                TaxonomyClassificationContinuationRequest.scope_node_id,
                TaxonomyClassificationContinuationRequest.node_id,
            ],
            set_={
                "source_job_id": statement.excluded.source_job_id,
                "last_error": None,
                "updated_at": statement.excluded.updated_at,
            },
        )
        await self._session.execute(statement)

    async def drain_continuation_requests(self, *, now: datetime) -> int:
        pending_count = await self._count_continuation_requests()
        if pending_count == 0:
            return 0
        oldest_updated_at = await self._oldest_continuation_request_updated_at()
        if (
            pending_count < self._continuation_request_batch_size
            and oldest_updated_at is not None
            and now - oldest_updated_at < self._continuation_flush_interval
        ):
            return 0

        requests = list(
            (
                await self._session.scalars(
                    select(TaxonomyClassificationContinuationRequest)
                    .order_by(
                        TaxonomyClassificationContinuationRequest.updated_at.asc(),
                        TaxonomyClassificationContinuationRequest.id.asc(),
                    )
                    .limit(self._continuation_request_batch_size)
                    .with_for_update(skip_locked=True)
                )
            ).all()
        )
        prepared_submissions: list[_PreparedContinuationSubmission] = []
        for request in requests:
            prepared_submission = await self._prepare_continuation_submission(
                request=request,
                now=now,
            )
            if prepared_submission is not None:
                prepared_submissions.append(prepared_submission)
        await self._session.flush()
        if prepared_submissions:
            await self._session.commit()
            try:
                await self._submission_service().submit_existing_jobs(
                    submissions=[item.submission for item in prepared_submissions],
                    batch_size=self._continuation_request_batch_size,
                )
            except JobQueueMCPClientError as exc:
                await self._record_continuation_submission_error(
                    request_ids=[item.request_id for item in prepared_submissions],
                    error=str(exc),
                    now=now,
                )
                return len(requests)
            for item in prepared_submissions:
                await self._delete_continuation_request(request_id=item.request_id)
            await self._session.flush()
        return len(requests)

    async def _count_continuation_requests(self) -> int:
        count = await self._session.scalar(
            select(func.count()).select_from(TaxonomyClassificationContinuationRequest)
        )
        return int(count or 0)

    async def _oldest_continuation_request_updated_at(self) -> datetime | None:
        return await self._session.scalar(
            select(TaxonomyClassificationContinuationRequest.updated_at)
            .order_by(
                TaxonomyClassificationContinuationRequest.updated_at.asc(),
                TaxonomyClassificationContinuationRequest.id.asc(),
            )
            .limit(1)
        )

    async def _prepare_continuation_submission(
        self,
        *,
        request: TaxonomyClassificationContinuationRequest,
        now: datetime,
    ) -> _PreparedContinuationSubmission | None:
        request_id = request.id
        scope_node_id = request.scope_node_id
        node_id = request.node_id
        next_job_id = request.next_job_id

        assignment = await self._assignment_for_update(node_id=node_id)
        if assignment is None or assignment.taxonomy_node_id != scope_node_id:
            await self._delete_continuation_request(request_id=request_id)
            return None

        try:
            resolved_scope = await resolve_taxonomy_classification_scope_by_node_id(
                self._session,
                scope_node_id,
            )
        except TaxonomyClassificationScopeResolutionError:
            await self._delete_continuation_request(request_id=request_id)
            return None
        if not resolved_scope.regular_children:
            await self._delete_continuation_request(request_id=request_id)
            return None

        active_job = await self._active_job_for_scope_node(
            scope_node_id=scope_node_id,
            node_id=node_id,
        )
        if active_job is not None:
            if active_job.id != next_job_id or active_job.job_id is not None:
                await self._delete_continuation_request(request_id=request_id)
                return None
            local_job = active_job
        else:
            local_job = TaxonomyClassificationJob(
                scope_node_id=scope_node_id,
                node_id=node_id,
            )
            self._session.add(local_job)
            await self._session.flush()
            request.next_job_id = local_job.id
            request.last_error = None
            request.updated_at = now
            await self._session.flush()

        card = await self._session.get(Node, node_id)
        if card is None:
            await self._delete_continuation_request(request_id=request_id)
            return None
        return _PreparedContinuationSubmission(
            request_id=request_id,
            submission=TaxonomyClassificationExistingJobSubmission(
                resolved_scope=resolved_scope,
                local_job=local_job,
                card=card,
            ),
        )

    async def _record_continuation_submission_error(
        self,
        *,
        request_ids: Sequence[int],
        error: str,
        now: datetime,
    ) -> None:
        for request_id in request_ids:
            request_for_error = await self._continuation_request_for_update(request_id=request_id)
            if request_for_error is not None:
                request_for_error.last_error = error
                request_for_error.updated_at = now
        await self._session.flush()

    async def _assignment_for_update(self, *, node_id: int) -> NodeTaxonomyAssignment | None:
        return await self._session.scalar(
            select(NodeTaxonomyAssignment)
            .where(NodeTaxonomyAssignment.node_id == node_id)
            .limit(1)
            .with_for_update()
        )

    async def _active_job_for_scope_node(
        self,
        *,
        scope_node_id: int,
        node_id: int,
    ) -> TaxonomyClassificationJob | None:
        return await self._session.scalar(
            select(TaxonomyClassificationJob)
            .where(TaxonomyClassificationJob.scope_node_id == scope_node_id)
            .where(TaxonomyClassificationJob.node_id == node_id)
            .where(TaxonomyClassificationJob.processed_at.is_(None))
            .where(TaxonomyClassificationJob.terminal_state.is_(None))
            .order_by(TaxonomyClassificationJob.id.asc())
            .limit(1)
            .with_for_update()
        )

    async def _continuation_request_for_update(
        self,
        *,
        request_id: int,
    ) -> TaxonomyClassificationContinuationRequest | None:
        return await self._session.scalar(
            select(TaxonomyClassificationContinuationRequest)
            .where(TaxonomyClassificationContinuationRequest.id == request_id)
            .limit(1)
            .with_for_update()
        )

    async def _delete_continuation_request(self, *, request_id: int) -> None:
        request = await self._continuation_request_for_update(request_id=request_id)
        if request is not None:
            await self._session.delete(request)

    def _submission_service(self) -> TaxonomyClassificationSubmissionService:
        if self._queue_name is None:
            raise RuntimeError("taxonomy-classification queue_name is required.")
        return TaxonomyClassificationSubmissionService(
            self._session,
            job_queue_client=self._job_queue_client,
            queue_name=self._queue_name,
        )

    async def _record_projection_refresh_requests(
        self,
        *,
        scope_identities: Sequence[TaxonomyScopeIdentity],
        now: datetime,
    ) -> None:
        unique_scope_identities = sorted(
            set(scope_identities),
            key=lambda item: (item.scope_kind, item.taxonomy_node_id),
        )
        if not unique_scope_identities:
            return
        statement = pg_insert(TaxonomyClassificationProjectionRefreshRequest).values(
            [
                {
                    "scope_kind": scope_identity.scope_kind,
                    "taxonomy_node_id": scope_identity.taxonomy_node_id,
                    "last_error": None,
                    "created_at": now,
                    "updated_at": now,
                }
                for scope_identity in unique_scope_identities
            ]
        )
        statement = statement.on_conflict_do_update(
            index_elements=[
                TaxonomyClassificationProjectionRefreshRequest.scope_kind,
                TaxonomyClassificationProjectionRefreshRequest.taxonomy_node_id,
            ],
            set_={
                "last_error": None,
                "updated_at": statement.excluded.updated_at,
            },
        )
        await self._session.execute(statement)

    async def drain_projection_refresh_requests(self, *, now: datetime) -> int:
        requests = list(
            (
                await self._session.scalars(
                    select(TaxonomyClassificationProjectionRefreshRequest)
                    .order_by(
                        TaxonomyClassificationProjectionRefreshRequest.updated_at.asc(),
                        TaxonomyClassificationProjectionRefreshRequest.scope_kind.asc(),
                        TaxonomyClassificationProjectionRefreshRequest.taxonomy_node_id.asc(),
                    )
                    .limit(self._projection_refresh_batch_size)
                    .with_for_update(skip_locked=True)
                )
            ).all()
        )
        refreshed_count = 0
        for request in requests:
            try:
                await self._refresh_scope_projection(
                    scope_identity=TaxonomyScopeIdentity(
                        scope_kind=request.scope_kind,
                        taxonomy_node_id=request.taxonomy_node_id,
                    )
                )
            except Exception as exc:
                request.last_error = str(exc)
                request.updated_at = now
                continue
            await self._session.delete(request)
            refreshed_count += 1

        await self._session.flush()
        return refreshed_count

    async def _refresh_scope_projection(self, *, scope_identity: TaxonomyScopeIdentity) -> None:
        taxonomy_repo = TaxonomyRepo(session=self._session)
        knowledge_repo = KnowledgeRepo(session=self._session)
        inner_node_ids = await taxonomy_repo.list_assigned_node_ids_for_scope(
            scope_identity=scope_identity
        )
        adjacent_edge_ids = await knowledge_repo.fetch_adjacent_edge_ids_for_node_ids(
            node_ids=inner_node_ids
        )
        await taxonomy_repo.clear_projected_edge_ids_for_scope(scope_identity=scope_identity)
        await taxonomy_repo.add_projected_edge_ids_for_scope(
            scope_identity=scope_identity,
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


def _accepted_result_from_item(item: ResultReadItem) -> AcceptedTaxonomyClassificationJobResult:
    if item.status != "ready":
        raise ValueError(f"Job {item.job_id} result is not ready.")
    if item.submission_id is None or item.received_at is None or item.result_payload is None:
        raise ValueError(f"Job {item.job_id} ready result is missing required fields.")
    return AcceptedTaxonomyClassificationJobResult(
        job_id=item.job_id,
        submission_id=item.submission_id,
        received_at=item.received_at,
        result_payload=item.result_payload,
    )


def _chunks[T](items: Sequence[T], size: int) -> list[Sequence[T]]:
    return [items[index : index + size] for index in range(0, len(items), size)]


def _validate_result_items(
    *,
    result_items: Sequence[ResultReadItem],
    requested_job_ids: Sequence[int],
) -> None:
    if len(result_items) != len(requested_job_ids):
        raise ValueError("Batch result read response length did not match request length.")
    for expected_index, item in enumerate(result_items):
        if item.index != expected_index:
            raise ValueError("Batch result read response indexes did not match request indexes.")
        if item.job_id != requested_job_ids[expected_index]:
            raise ValueError("Batch result read response job ids did not match request job ids.")


__all__ = ["TaxonomyClassificationRuntimeService"]
