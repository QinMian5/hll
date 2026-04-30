"""
Abstract: Operator-facing taxonomy-classification job submission orchestration.
Out of scope: Runtime result processing and webhook authentication.
"""

from __future__ import annotations

from typing import Protocol

from sqlalchemy import func, select
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


class TaxonomyClassificationCreateJobClientPort(Protocol):
    async def create_job(
        self,
        *,
        queue_name: str,
        instruction: str,
        output_schema: dict[str, object],
        priority: str = "normal",
        payload: dict[str, object] | None = None,
        metadata: dict[str, object] | None = None,
    ) -> int: ...


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
    ) -> TaxonomyClassificationSubmissionResult:
        resolved_scopes = await resolve_taxonomy_classification_scopes(self._session, selection)
        summaries: list[TaxonomyClassificationScopeSummary] = []
        submitted_total = 0
        already_linked_total = 0
        skipped_no_children = 0

        for resolved_scope in resolved_scopes:
            already_linked_count = await self._count_already_linked_cards(
                resolved_scope=resolved_scope
            )
            already_linked_total += already_linked_count

            if not resolved_scope.regular_children:
                skipped_no_children += 1
                summaries.append(
                    TaxonomyClassificationScopeSummary(
                        scope_node_id=resolved_scope.scope_node.id,
                        breadcrumb=resolved_scope.breadcrumb,
                        regular_child_count=0,
                        submitted_count=0,
                        already_linked_count=already_linked_count,
                        skipped_no_children=True,
                    )
                )
                continue

            remaining_limit = _remaining_limit(limit=limit, submitted_count=submitted_total)
            submitted_count = await self._submit_resolved_scope_jobs(
                resolved_scope=resolved_scope,
                limit=remaining_limit,
            )
            submitted_total += submitted_count
            summaries.append(
                TaxonomyClassificationScopeSummary(
                    scope_node_id=resolved_scope.scope_node.id,
                    breadcrumb=resolved_scope.breadcrumb,
                    regular_child_count=len(resolved_scope.regular_children),
                    submitted_count=submitted_count,
                    already_linked_count=already_linked_count,
                    skipped_no_children=False,
                )
            )

        return TaxonomyClassificationSubmissionResult(
            selected_scope_count=len(resolved_scopes),
            submitted_count=submitted_total,
            already_linked_count=already_linked_total,
            skipped_no_children=skipped_no_children,
            scopes=summaries,
        )

    async def _submit_resolved_scope_jobs(
        self,
        *,
        resolved_scope: ResolvedTaxonomyClassificationScope,
        limit: int | None,
    ) -> int:
        if limit == 0:
            return 0

        pending_jobs = await self._list_pending_local_jobs(
            source_unclassified_node_id=resolved_scope.source_unclassified_node.id,
            scope_node_id=resolved_scope.scope_node.id,
            limit=limit,
        )
        submitted_count = await self._submit_pending_jobs(
            resolved_scope=resolved_scope,
            pending_jobs=pending_jobs,
        )

        remaining_limit = _remaining_limit(limit=limit, submitted_count=submitted_count)
        if remaining_limit == 0:
            return submitted_count

        cards = await self._list_cards_without_active_job(
            source_unclassified_node_id=resolved_scope.source_unclassified_node.id,
            scope_node_id=resolved_scope.scope_node.id,
            limit=remaining_limit,
        )
        created_pending_jobs = await self._create_pending_jobs(
            resolved_scope=resolved_scope,
            cards=cards,
        )
        submitted_count += await self._submit_pending_jobs(
            resolved_scope=resolved_scope,
            pending_jobs=created_pending_jobs,
        )
        return submitted_count

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
    ) -> int:
        submitted_count = 0
        for local_job, card in pending_jobs:
            payload = TaxonomyClassificationJobPayload(
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
            metadata: dict[str, object] = {
                "scope_node_id": resolved_scope.scope_node.id,
                "source_unclassified_node_id": resolved_scope.source_unclassified_node.id,
                "node_id": card.id,
            }
            job_id = await self._job_queue_client.create_job(
                queue_name=self._queue_name,
                priority="normal",
                instruction=build_taxonomy_classification_instruction(),
                output_schema=export_taxonomy_classification_output_schema(),
                payload=payload.model_dump(mode="json"),
                metadata=metadata,
            )
            local_job.job_id = job_id
            await self._session.flush()
            await self._session.commit()
            submitted_count += 1

        return submitted_count

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


def _remaining_limit(*, limit: int | None, submitted_count: int) -> int | None:
    if limit is None:
        return None
    return max(limit - submitted_count, 0)


__all__ = ["TaxonomyClassificationSubmissionService"]
