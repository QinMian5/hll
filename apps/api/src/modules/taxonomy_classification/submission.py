"""
Abstract: Operator-facing taxonomy-classification job submission orchestration.
Out of scope: Runtime result processing and webhook authentication.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Literal, Protocol

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from modules.knowledge_graph.model import Node
from modules.taxonomy.model import NodeTaxonomyAssignment, TaxonomyNode
from modules.taxonomy.repo import UNCLASSIFIED_NODE_NAME
from modules.taxonomy_classification.contracts import (
    TaxonomyClassificationCardPayload,
    TaxonomyClassificationJobPayload,
    TaxonomyClassificationNodeRef,
    export_taxonomy_classification_output_schema,
)
from modules.taxonomy_classification.instruction import build_taxonomy_classification_instruction
from modules.taxonomy_classification.model import TaxonomyClassificationJob


class TaxonomyClassificationCreateJobClientPort(Protocol):
    async def create_job(
        self,
        *,
        queue_name: str,
        priority: Literal["low", "normal", "high", "critical"],
        instruction: str,
        output_schema: Mapping[str, object],
        payload: Mapping[str, object],
        metadata: Mapping[str, object],
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

    async def submit_scope_refinement_jobs(
        self,
        *,
        scope_node_id: int,
        limit: int | None,
    ) -> int:
        scope_node = await self._require_scope_node(scope_node_id=scope_node_id)
        source_unclassified = await self._require_source_unclassified(scope_node=scope_node)
        children = await self._list_regular_children(scope_node_id=scope_node.id)
        cards = await self._list_cards_without_active_job(
            source_unclassified_node_id=source_unclassified.id,
            scope_node_id=scope_node.id,
            limit=limit,
        )

        for card in cards:
            self._session.add(
                TaxonomyClassificationJob(
                    scope_node_id=scope_node.id,
                    source_unclassified_node_id=source_unclassified.id,
                    node_id=card.id,
                )
            )
        if cards:
            await self._session.flush()
            await self._session.commit()

        pending_jobs = await self._list_pending_local_jobs(
            source_unclassified_node_id=source_unclassified.id,
            scope_node_id=scope_node.id,
            limit=limit,
        )

        submitted_count = 0
        for local_job, card in pending_jobs:
            payload = TaxonomyClassificationJobPayload(
                scope_node=TaxonomyClassificationNodeRef(
                    id=scope_node.id,
                    name=scope_node.name,
                ),
                source_unclassified_node=TaxonomyClassificationNodeRef(
                    id=source_unclassified.id,
                    name=source_unclassified.name,
                ),
                card=TaxonomyClassificationCardPayload(
                    id=card.id,
                    title=card.title,
                    content=card.content,
                ),
                children=[
                    TaxonomyClassificationNodeRef(id=child.id, name=child.name)
                    for child in children
                ],
                allow_unclassified=True,
            )
            metadata = {
                "scope_node_id": scope_node.id,
                "source_unclassified_node_id": source_unclassified.id,
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

    async def _require_scope_node(self, *, scope_node_id: int) -> TaxonomyNode:
        scope_node = await self._session.get(TaxonomyNode, scope_node_id)
        if scope_node is None:
            raise ValueError(f"Taxonomy scope node {scope_node_id} does not exist.")
        if scope_node.is_leaf:
            raise ValueError("Taxonomy refinement scope must be a regular node.")
        return scope_node

    async def _require_source_unclassified(self, *, scope_node: TaxonomyNode) -> TaxonomyNode:
        source_unclassified = await self._session.scalar(
            select(TaxonomyNode)
            .where(TaxonomyNode.parent_id == scope_node.id)
            .where(TaxonomyNode.name == UNCLASSIFIED_NODE_NAME)
            .where(TaxonomyNode.is_leaf.is_(True))
            .limit(1)
        )
        if source_unclassified is None:
            raise ValueError("Taxonomy scope node is missing its Unclassified leaf.")
        return source_unclassified

    async def _list_regular_children(self, *, scope_node_id: int) -> list[TaxonomyNode]:
        return list(
            await self._session.scalars(
                select(TaxonomyNode)
                .where(TaxonomyNode.parent_id == scope_node_id)
                .where(TaxonomyNode.name != UNCLASSIFIED_NODE_NAME)
                .where(TaxonomyNode.is_leaf.is_(False))
                .order_by(TaxonomyNode.name.asc(), TaxonomyNode.id.asc())
            )
        )

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


__all__ = ["TaxonomyClassificationSubmissionService"]
