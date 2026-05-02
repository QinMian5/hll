"""
Abstract: Operator-facing taxonomy-classification job submission orchestration.
Out of scope: Runtime result processing and webhook authentication.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Protocol

from job_queue_mcp_client.types import CreatedJob, CreateJobItem
from sqlalchemy import and_, func, select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession

from modules.knowledge_graph.model import Node
from modules.taxonomy.model import NodeTaxonomyAssignment
from modules.taxonomy_classification.contracts import (
    TaxonomyClassificationCardPayload,
    TaxonomyClassificationChildPayload,
    TaxonomyClassificationJobPayload,
    export_taxonomy_classification_output_schema,
)
from modules.taxonomy_classification.dto import (
    TaxonomyClassificationScopeSummary,
    TaxonomyClassificationSubmissionResult,
    TaxonomyClassificationSubmissionSelection,
)
from modules.taxonomy_classification.instruction import build_taxonomy_classification_instruction
from modules.taxonomy_classification.model import TaxonomyClassificationJob
from modules.taxonomy_classification.scope_resolution import (
    ResolvedTaxonomyClassificationScope,
    resolve_taxonomy_classification_scopes,
)

MAX_JOB_QUEUE_BATCH_SIZE = 1000
MAX_JOB_QUEUE_BATCH_REQUEST_BYTES = 900 * 1024
_JOB_BATCH_REQUEST_PREFIX_BYTES = len(b'{"jobs":[')
_JOB_BATCH_REQUEST_SUFFIX_BYTES = len(b"]}")


@dataclass(frozen=True, slots=True)
class _SubmissionCounts:
    submitted_count: int = 0
    reused_idempotent_count: int = 0

    @property
    def total_count(self) -> int:
        return self.submitted_count + self.reused_idempotent_count


@dataclass(frozen=True, slots=True)
class _PendingSubmissionItem:
    local_job: TaxonomyClassificationJob
    card: Node
    create_job: CreateJobItem


@dataclass(frozen=True, slots=True)
class _ScopeSubmissionPreflight:
    pending_local_count: int = 0
    candidate_without_active_job_count: int = 0
    already_linked_count: int = 0

    @property
    def jobs_to_link_count(self) -> int:
        return self.pending_local_count + self.candidate_without_active_job_count


class TaxonomyClassificationCreateJobClientPort(Protocol):
    async def create_jobs(self, jobs: Sequence[CreateJobItem]) -> Sequence[CreatedJob]: ...


class TaxonomyClassificationSubmissionService:
    def __init__(
        self,
        session: AsyncSession,
        *,
        job_queue_client: TaxonomyClassificationCreateJobClientPort,
        queue_name: str,
    ) -> None:
        self._session = session
        self._job_queue_client = job_queue_client
        self._queue_name = queue_name

    async def submit_refinement_jobs(
        self,
        *,
        selection: TaxonomyClassificationSubmissionSelection,
        limit: int | None,
        batch_size: int = MAX_JOB_QUEUE_BATCH_SIZE,
        progress_total_callback: Callable[[int], None] | None = None,
        progress_advance_callback: Callable[[int], None] | None = None,
    ) -> TaxonomyClassificationSubmissionResult:
        if batch_size < 1 or batch_size > MAX_JOB_QUEUE_BATCH_SIZE:
            raise ValueError("batch_size must be between 1 and 1000")

        resolved_scopes = await resolve_taxonomy_classification_scopes(self._session, selection)
        preflight_by_scope = await self._load_submission_preflight(
            resolved_scopes=resolved_scopes,
        )
        total_jobs_to_link = _count_jobs_to_link_from_preflight(
            resolved_scopes=resolved_scopes,
            preflight_by_scope=preflight_by_scope,
            limit=limit,
        )
        if progress_total_callback is not None:
            progress_total_callback(total_jobs_to_link)

        summaries: list[TaxonomyClassificationScopeSummary] = []
        submitted_total = 0
        reused_idempotent_total = 0
        linked_total = 0
        already_linked_total = 0
        skipped_no_children = 0

        for resolved_scope in resolved_scopes:
            preflight = preflight_by_scope[_scope_key(resolved_scope)]
            already_linked_count = preflight.already_linked_count
            already_linked_total += already_linked_count

            if not resolved_scope.regular_children:
                skipped_no_children += 1
                summaries.append(
                    TaxonomyClassificationScopeSummary(
                        scope_node_id=resolved_scope.scope_node.id,
                        breadcrumb=resolved_scope.breadcrumb,
                        regular_child_count=0,
                        submitted_count=0,
                        reused_idempotent_count=0,
                        already_linked_count=already_linked_count,
                        skipped_no_children=True,
                    )
                )
                continue

            remaining_limit = _remaining_limit(limit=limit, submitted_count=linked_total)
            if remaining_limit == 0 or preflight.jobs_to_link_count == 0:
                counts = _SubmissionCounts()
            else:
                counts = await self._submit_resolved_scope_jobs(
                    resolved_scope=resolved_scope,
                    limit=remaining_limit,
                    batch_size=batch_size,
                    progress_advance_callback=progress_advance_callback,
                )
            submitted_total += counts.submitted_count
            reused_idempotent_total += counts.reused_idempotent_count
            linked_total += counts.total_count
            summaries.append(
                TaxonomyClassificationScopeSummary(
                    scope_node_id=resolved_scope.scope_node.id,
                    breadcrumb=resolved_scope.breadcrumb,
                    regular_child_count=len(resolved_scope.regular_children),
                    submitted_count=counts.submitted_count,
                    reused_idempotent_count=counts.reused_idempotent_count,
                    already_linked_count=already_linked_count,
                    skipped_no_children=False,
                )
            )

        return TaxonomyClassificationSubmissionResult(
            selected_scope_count=len(resolved_scopes),
            submitted_count=submitted_total,
            reused_idempotent_count=reused_idempotent_total,
            already_linked_count=already_linked_total,
            skipped_no_children=skipped_no_children,
            scopes=summaries,
        )

    async def _load_submission_preflight(
        self,
        *,
        resolved_scopes: Sequence[ResolvedTaxonomyClassificationScope],
    ) -> dict[tuple[int, int], _ScopeSubmissionPreflight]:
        scope_pairs = [_scope_key(resolved_scope) for resolved_scope in resolved_scopes]
        if not scope_pairs:
            return {}

        pending_counts: dict[tuple[int, int], int] = {}
        pending_rows = await self._session.execute(
            select(
                TaxonomyClassificationJob.scope_node_id,
                TaxonomyClassificationJob.source_unclassified_node_id,
                func.count(TaxonomyClassificationJob.id),
            )
            .where(
                tuple_(
                    TaxonomyClassificationJob.scope_node_id,
                    TaxonomyClassificationJob.source_unclassified_node_id,
                ).in_(scope_pairs)
            )
            .where(TaxonomyClassificationJob.job_id.is_(None))
            .where(TaxonomyClassificationJob.processed_at.is_(None))
            .where(TaxonomyClassificationJob.terminal_state.is_(None))
            .group_by(
                TaxonomyClassificationJob.scope_node_id,
                TaxonomyClassificationJob.source_unclassified_node_id,
            )
        )
        for scope_node_id, source_unclassified_node_id, count in pending_rows:
            pending_counts[(scope_node_id, source_unclassified_node_id)] = int(count or 0)

        source_to_scope_key = {
            resolved_scope.source_unclassified_node.id: _scope_key(resolved_scope)
            for resolved_scope in resolved_scopes
        }
        active_jobs = (
            select(
                TaxonomyClassificationJob.scope_node_id,
                TaxonomyClassificationJob.source_unclassified_node_id,
                TaxonomyClassificationJob.node_id,
                TaxonomyClassificationJob.job_id,
            )
            .where(
                tuple_(
                    TaxonomyClassificationJob.scope_node_id,
                    TaxonomyClassificationJob.source_unclassified_node_id,
                ).in_(scope_pairs)
            )
            .where(TaxonomyClassificationJob.processed_at.is_(None))
            .where(TaxonomyClassificationJob.terminal_state.is_(None))
            .subquery()
        )
        assignment_rows = await self._session.execute(
            select(
                NodeTaxonomyAssignment.taxonomy_node_id,
                func.count(NodeTaxonomyAssignment.node_id).filter(active_jobs.c.node_id.is_(None)),
                func.count(NodeTaxonomyAssignment.node_id).filter(
                    active_jobs.c.job_id.is_not(None)
                ),
            )
            .outerjoin(
                active_jobs,
                and_(
                    active_jobs.c.source_unclassified_node_id
                    == NodeTaxonomyAssignment.taxonomy_node_id,
                    active_jobs.c.node_id == NodeTaxonomyAssignment.node_id,
                ),
            )
            .where(NodeTaxonomyAssignment.taxonomy_node_id.in_(source_to_scope_key))
            .group_by(NodeTaxonomyAssignment.taxonomy_node_id)
        )
        assignment_counts: dict[tuple[int, int], tuple[int, int]] = {}
        for source_unclassified_node_id, candidate_count, already_linked_count in assignment_rows:
            scope_key = source_to_scope_key[source_unclassified_node_id]
            assignment_counts[scope_key] = (
                int(candidate_count or 0),
                int(already_linked_count or 0),
            )

        return {
            scope_key: _ScopeSubmissionPreflight(
                pending_local_count=pending_counts.get(scope_key, 0),
                candidate_without_active_job_count=assignment_counts.get(scope_key, (0, 0))[0],
                already_linked_count=assignment_counts.get(scope_key, (0, 0))[1],
            )
            for scope_key in scope_pairs
        }

    async def _submit_resolved_scope_jobs(
        self,
        *,
        resolved_scope: ResolvedTaxonomyClassificationScope,
        limit: int | None,
        batch_size: int,
        progress_advance_callback: Callable[[int], None] | None,
    ) -> _SubmissionCounts:
        if limit == 0:
            return _SubmissionCounts()

        pending_jobs = await self._list_pending_local_jobs(
            source_unclassified_node_id=resolved_scope.source_unclassified_node.id,
            scope_node_id=resolved_scope.scope_node.id,
            limit=limit,
        )
        counts = await self._submit_pending_jobs(
            resolved_scope=resolved_scope,
            pending_jobs=pending_jobs,
            batch_size=batch_size,
            progress_advance_callback=progress_advance_callback,
        )

        remaining_limit = _remaining_limit(limit=limit, submitted_count=counts.total_count)
        if remaining_limit == 0:
            return counts

        cards = await self._list_cards_without_active_job(
            source_unclassified_node_id=resolved_scope.source_unclassified_node.id,
            scope_node_id=resolved_scope.scope_node.id,
            limit=remaining_limit,
        )
        created_pending_jobs = await self._create_pending_jobs(
            resolved_scope=resolved_scope,
            cards=cards,
        )
        created_counts = await self._submit_pending_jobs(
            resolved_scope=resolved_scope,
            pending_jobs=created_pending_jobs,
            batch_size=batch_size,
            progress_advance_callback=progress_advance_callback,
        )
        return _SubmissionCounts(
            submitted_count=counts.submitted_count + created_counts.submitted_count,
            reused_idempotent_count=(
                counts.reused_idempotent_count + created_counts.reused_idempotent_count
            ),
        )

    async def _create_pending_jobs(
        self,
        *,
        resolved_scope: ResolvedTaxonomyClassificationScope,
        cards: list[Node],
    ) -> list[tuple[TaxonomyClassificationJob, Node]]:
        pending_jobs: list[tuple[TaxonomyClassificationJob, Node]] = []
        for card in cards:
            local_job = TaxonomyClassificationJob(
                scope_node_id=resolved_scope.scope_node.id,
                source_unclassified_node_id=resolved_scope.source_unclassified_node.id,
                node_id=card.id,
            )
            self._session.add(local_job)
            pending_jobs.append((local_job, card))
        if pending_jobs:
            await self._session.flush()
            await self._session.commit()
        return pending_jobs

    async def _submit_pending_jobs(
        self,
        *,
        resolved_scope: ResolvedTaxonomyClassificationScope,
        pending_jobs: list[tuple[TaxonomyClassificationJob, Node]],
        batch_size: int,
        progress_advance_callback: Callable[[int], None] | None,
    ) -> _SubmissionCounts:
        submitted_count = 0
        reused_idempotent_count = 0
        instruction = build_taxonomy_classification_instruction()
        output_schema = export_taxonomy_classification_output_schema()

        pending_items = [
            _PendingSubmissionItem(
                local_job=local_job,
                card=card,
                create_job=CreateJobItem(
                    queue_name=self._queue_name,
                    idempotency_key=_idempotency_key(local_job),
                    priority="normal",
                    instruction=instruction,
                    output_schema=output_schema,
                    payload=self._job_payload(
                        resolved_scope=resolved_scope,
                        card=card,
                    ).model_dump(mode="json"),
                    metadata={
                        "scope_node_id": resolved_scope.scope_node.id,
                        "source_unclassified_node_id": (resolved_scope.source_unclassified_node.id),
                        "node_id": card.id,
                    },
                ),
            )
            for local_job, card in pending_jobs
        ]

        for batch in _chunk_submission_items(
            pending_items,
            max_item_count=batch_size,
            max_request_bytes=MAX_JOB_QUEUE_BATCH_REQUEST_BYTES,
        ):
            items = [entry.create_job for entry in batch]
            created_jobs = await self._job_queue_client.create_jobs(items)
            created_job_by_index = _created_job_by_index(
                created_jobs=created_jobs,
                expected_count=len(batch),
            )
            for index, entry in enumerate(batch):
                created_job = created_job_by_index[index]
                entry.local_job.job_id = created_job.job_id
                if created_job.created:
                    submitted_count += 1
                else:
                    reused_idempotent_count += 1
            await self._session.flush()
            await self._session.commit()
            if progress_advance_callback is not None:
                progress_advance_callback(len(batch))

        return _SubmissionCounts(
            submitted_count=submitted_count,
            reused_idempotent_count=reused_idempotent_count,
        )

    def _job_payload(
        self,
        *,
        resolved_scope: ResolvedTaxonomyClassificationScope,
        card: Node,
    ) -> TaxonomyClassificationJobPayload:
        return TaxonomyClassificationJobPayload(
            scope_path=" / ".join(resolved_scope.breadcrumb),
            card=TaxonomyClassificationCardPayload(
                title=card.title,
                content=card.content,
            ),
            children=[
                TaxonomyClassificationChildPayload(name=child.name)
                for child in resolved_scope.regular_children
            ]
            + [
                TaxonomyClassificationChildPayload(
                    name=resolved_scope.source_unclassified_node.name
                )
            ],
        )

    async def _count_jobs_to_link(
        self,
        *,
        resolved_scopes: Sequence[ResolvedTaxonomyClassificationScope],
        limit: int | None,
    ) -> int:
        total_count = 0
        for resolved_scope in resolved_scopes:
            if not resolved_scope.regular_children:
                continue

            remaining_limit = _remaining_limit(limit=limit, submitted_count=total_count)
            if remaining_limit == 0:
                break

            pending_count = await self._count_pending_local_jobs(
                source_unclassified_node_id=resolved_scope.source_unclassified_node.id,
                scope_node_id=resolved_scope.scope_node.id,
                limit=remaining_limit,
            )
            total_count += pending_count

            remaining_limit = _remaining_limit(limit=limit, submitted_count=total_count)
            if remaining_limit == 0:
                break

            total_count += await self._count_cards_without_active_job(
                source_unclassified_node_id=resolved_scope.source_unclassified_node.id,
                scope_node_id=resolved_scope.scope_node.id,
                limit=remaining_limit,
            )
        return total_count

    async def _list_cards_without_active_job(
        self,
        *,
        source_unclassified_node_id: int,
        scope_node_id: int,
        limit: int | None,
    ) -> list[Node]:
        active_jobs = (
            select(TaxonomyClassificationJob.node_id)
            .where(TaxonomyClassificationJob.scope_node_id == scope_node_id)
            .where(
                TaxonomyClassificationJob.source_unclassified_node_id == source_unclassified_node_id
            )
            .where(TaxonomyClassificationJob.processed_at.is_(None))
            .where(TaxonomyClassificationJob.terminal_state.is_(None))
        )
        statement = (
            select(Node)
            .join(NodeTaxonomyAssignment, NodeTaxonomyAssignment.node_id == Node.id)
            .where(NodeTaxonomyAssignment.taxonomy_node_id == source_unclassified_node_id)
            .where(Node.id.not_in(active_jobs))
            .order_by(Node.id.asc())
        )
        if limit is not None:
            statement = statement.limit(limit)
        return list(await self._session.scalars(statement))

    async def _count_cards_without_active_job(
        self,
        *,
        source_unclassified_node_id: int,
        scope_node_id: int,
        limit: int | None,
    ) -> int:
        active_jobs = (
            select(TaxonomyClassificationJob.node_id)
            .where(TaxonomyClassificationJob.scope_node_id == scope_node_id)
            .where(
                TaxonomyClassificationJob.source_unclassified_node_id == source_unclassified_node_id
            )
            .where(TaxonomyClassificationJob.processed_at.is_(None))
            .where(TaxonomyClassificationJob.terminal_state.is_(None))
        )
        candidate_ids = (
            select(Node.id)
            .join(NodeTaxonomyAssignment, NodeTaxonomyAssignment.node_id == Node.id)
            .where(NodeTaxonomyAssignment.taxonomy_node_id == source_unclassified_node_id)
            .where(Node.id.not_in(active_jobs))
            .order_by(Node.id.asc())
        )
        if limit is not None:
            candidate_ids = candidate_ids.limit(limit)
        count = await self._session.scalar(
            select(func.count()).select_from(candidate_ids.subquery())
        )
        return int(count or 0)

    async def _count_already_linked_cards(
        self,
        *,
        resolved_scope: ResolvedTaxonomyClassificationScope,
    ) -> int:
        active_remote_jobs = (
            select(TaxonomyClassificationJob.node_id)
            .where(TaxonomyClassificationJob.scope_node_id == resolved_scope.scope_node.id)
            .where(
                TaxonomyClassificationJob.source_unclassified_node_id
                == resolved_scope.source_unclassified_node.id
            )
            .where(TaxonomyClassificationJob.job_id.is_not(None))
            .where(TaxonomyClassificationJob.processed_at.is_(None))
            .where(TaxonomyClassificationJob.terminal_state.is_(None))
        )
        count = await self._session.scalar(
            select(func.count(func.distinct(Node.id)))
            .join(NodeTaxonomyAssignment, NodeTaxonomyAssignment.node_id == Node.id)
            .where(
                NodeTaxonomyAssignment.taxonomy_node_id
                == resolved_scope.source_unclassified_node.id
            )
            .where(Node.id.in_(active_remote_jobs))
        )
        return int(count or 0)

    async def _list_pending_local_jobs(
        self,
        *,
        source_unclassified_node_id: int,
        scope_node_id: int,
        limit: int | None,
    ) -> list[tuple[TaxonomyClassificationJob, Node]]:
        statement = (
            select(TaxonomyClassificationJob, Node)
            .join(Node, Node.id == TaxonomyClassificationJob.node_id)
            .where(TaxonomyClassificationJob.scope_node_id == scope_node_id)
            .where(
                TaxonomyClassificationJob.source_unclassified_node_id == source_unclassified_node_id
            )
            .where(TaxonomyClassificationJob.job_id.is_(None))
            .where(TaxonomyClassificationJob.processed_at.is_(None))
            .where(TaxonomyClassificationJob.terminal_state.is_(None))
            .order_by(TaxonomyClassificationJob.id.asc())
            .with_for_update(skip_locked=True)
        )
        if limit is not None:
            statement = statement.limit(limit)
        return [(job, node) for job, node in await self._session.execute(statement)]

    async def _count_pending_local_jobs(
        self,
        *,
        source_unclassified_node_id: int,
        scope_node_id: int,
        limit: int | None,
    ) -> int:
        candidate_ids = (
            select(TaxonomyClassificationJob.id)
            .join(Node, Node.id == TaxonomyClassificationJob.node_id)
            .where(TaxonomyClassificationJob.scope_node_id == scope_node_id)
            .where(
                TaxonomyClassificationJob.source_unclassified_node_id == source_unclassified_node_id
            )
            .where(TaxonomyClassificationJob.job_id.is_(None))
            .where(TaxonomyClassificationJob.processed_at.is_(None))
            .where(TaxonomyClassificationJob.terminal_state.is_(None))
            .order_by(TaxonomyClassificationJob.id.asc())
        )
        if limit is not None:
            candidate_ids = candidate_ids.limit(limit)
        count = await self._session.scalar(
            select(func.count()).select_from(candidate_ids.subquery())
        )
        return int(count or 0)


def _remaining_limit(*, limit: int | None, submitted_count: int) -> int | None:
    if limit is None:
        return None
    return max(limit - submitted_count, 0)


def _scope_key(resolved_scope: ResolvedTaxonomyClassificationScope) -> tuple[int, int]:
    return (resolved_scope.scope_node.id, resolved_scope.source_unclassified_node.id)


def _count_jobs_to_link_from_preflight(
    *,
    resolved_scopes: Sequence[ResolvedTaxonomyClassificationScope],
    preflight_by_scope: dict[tuple[int, int], _ScopeSubmissionPreflight],
    limit: int | None,
) -> int:
    total_count = 0
    for resolved_scope in resolved_scopes:
        if not resolved_scope.regular_children:
            continue

        remaining_limit = _remaining_limit(limit=limit, submitted_count=total_count)
        if remaining_limit == 0:
            break

        scope_count = preflight_by_scope[_scope_key(resolved_scope)].jobs_to_link_count
        if remaining_limit is None:
            total_count += scope_count
        else:
            total_count += min(scope_count, remaining_limit)
    return total_count


def _idempotency_key(local_job: TaxonomyClassificationJob) -> str:
    if local_job.id is None:
        raise RuntimeError("Local taxonomy-classification job must be flushed before submission.")
    return f"taxonomy-classification-job:{local_job.id}"


def _chunk_submission_items(
    items: Sequence[_PendingSubmissionItem],
    *,
    max_item_count: int,
    max_request_bytes: int,
) -> list[list[_PendingSubmissionItem]]:
    chunks: list[list[_PendingSubmissionItem]] = []
    current: list[_PendingSubmissionItem] = []
    current_request_bytes = _empty_batch_request_size_bytes()

    for item in items:
        item_json_bytes = _create_job_item_size_bytes(item.create_job)
        single_item_request_bytes = _empty_batch_request_size_bytes() + item_json_bytes
        if single_item_request_bytes > max_request_bytes:
            raise ValueError(
                "single taxonomy-classification job request "
                f"local_job_id={item.local_job.id} node_id={item.card.id} "
                f"is {single_item_request_bytes} bytes, exceeding max producer batch "
                f"request size {max_request_bytes} bytes"
            )

        candidate_request_bytes = current_request_bytes + item_json_bytes
        if current:
            candidate_request_bytes += 1

        if current and (
            len(current) >= max_item_count or candidate_request_bytes > max_request_bytes
        ):
            chunks.append(current)
            current = [item]
            current_request_bytes = _empty_batch_request_size_bytes() + item_json_bytes
            continue

        current.append(item)
        current_request_bytes = candidate_request_bytes

    if current:
        chunks.append(current)

    return chunks


def _empty_batch_request_size_bytes() -> int:
    return _JOB_BATCH_REQUEST_PREFIX_BYTES + _JOB_BATCH_REQUEST_SUFFIX_BYTES


def _create_job_item_size_bytes(item: CreateJobItem) -> int:
    return len(
        json.dumps(
            _create_job_item_request_dict(item),
            ensure_ascii=True,
            separators=(",", ":"),
        ).encode("utf-8")
    )


def _create_job_item_request_dict(item: CreateJobItem) -> dict[str, object]:
    return {
        "queue_name": item.queue_name,
        "idempotency_key": item.idempotency_key,
        "instruction": item.instruction,
        "output_schema": item.output_schema,
        "priority": item.priority,
        "payload": item.payload or {},
        "metadata": item.metadata or {},
    }


def _created_job_by_index(
    *,
    created_jobs: Sequence[CreatedJob],
    expected_count: int,
) -> dict[int, CreatedJob]:
    if len(created_jobs) != expected_count:
        raise ValueError("Batch job creation response length did not match request length.")
    created_job_by_index = {created_job.index: created_job for created_job in created_jobs}
    expected_indexes = set(range(expected_count))
    if set(created_job_by_index) != expected_indexes:
        raise ValueError("Batch job creation response indexes did not match request indexes.")
    return created_job_by_index


__all__ = ["TaxonomyClassificationSubmissionService"]
