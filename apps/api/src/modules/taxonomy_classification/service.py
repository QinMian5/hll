"""
Abstract: Batch orchestration service for operator-triggered taxonomy classification.
Out of scope: Click command parsing and cursor-agent prompt construction details.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable

from modules.taxonomy_classification.dto import (
    TaxonomyClassificationBatchResult,
    TaxonomyClassificationNodeOutcome,
)
from modules.taxonomy_classification.ports import (
    CursorClassificationRunnerPort,
    TaxonomyClassificationKnowledgePort,
    TaxonomyClassificationStatusPort,
)


class TaxonomyClassificationService:
    def __init__(
        self,
        *,
        knowledge_port: TaxonomyClassificationKnowledgePort,
        cursor_runner: CursorClassificationRunnerPort,
        taxonomy_status_port: TaxonomyClassificationStatusPort,
        default_max_workers: int,
    ) -> None:
        if default_max_workers < 1:
            raise ValueError("default_max_workers must be >= 1")
        self._knowledge_port = knowledge_port
        self._cursor_runner = cursor_runner
        self._taxonomy_status_port = taxonomy_status_port
        self._default_max_workers = default_max_workers

    async def classify_unassigned(
        self,
        *,
        limit: int | None,
        max_workers: int | None,
        on_selection_resolved: Callable[[int], None] | None = None,
        on_node_finished: Callable[[TaxonomyClassificationNodeOutcome], None] | None = None,
    ) -> TaxonomyClassificationBatchResult:
        resolved_max_workers = max_workers or self._default_max_workers
        if resolved_max_workers < 1:
            raise ValueError("max_workers must be >= 1")

        selected_nodes = (
            await self._knowledge_port.list_unassigned_nodes_for_taxonomy_classification(
                limit=limit,
            )
        )
        if on_selection_resolved is not None:
            on_selection_resolved(len(selected_nodes))

        if not selected_nodes:
            return TaxonomyClassificationBatchResult(
                selected_count=0,
                assigned_count=0,
                unchanged_count=0,
                error_count=0,
                selected_node_ids=[],
                outcomes=[],
            )

        semaphore = asyncio.Semaphore(resolved_max_workers)
        outcomes: list[TaxonomyClassificationNodeOutcome | None] = [None] * len(selected_nodes)

        async def _process_node(index: int) -> None:
            node = selected_nodes[index]
            async with semaphore:
                assignment_before = await self._taxonomy_status_port.get_assignment_for_node(
                    node_id=node.node_id
                )
                try:
                    await self._cursor_runner.run_node_session(node=node)
                    assignment_after = await self._taxonomy_status_port.get_assignment_for_node(
                        node_id=node.node_id
                    )
                    if assignment_after is None:
                        outcome = TaxonomyClassificationNodeOutcome(
                            node_id=node.node_id,
                            status="error",
                            detail="assignment missing after cursor session",
                        )
                    elif assignment_before is None:
                        outcome = TaxonomyClassificationNodeOutcome(
                            node_id=node.node_id,
                            status="assigned",
                            taxonomy_node_id=assignment_after.taxonomy_node.id,
                        )
                    else:
                        outcome = TaxonomyClassificationNodeOutcome(
                            node_id=node.node_id,
                            status="already_assigned",
                            taxonomy_node_id=assignment_after.taxonomy_node.id,
                        )
                except Exception as exc:
                    detail = str(exc).strip() or exc.__class__.__name__
                    outcome = TaxonomyClassificationNodeOutcome(
                        node_id=node.node_id,
                        status="error",
                        detail=detail,
                    )

            outcomes[index] = outcome
            if on_node_finished is not None:
                on_node_finished(outcome)

        await asyncio.gather(*[_process_node(index) for index in range(len(selected_nodes))])
        finalized_outcomes = [outcome for outcome in outcomes if outcome is not None]

        return TaxonomyClassificationBatchResult(
            selected_count=len(selected_nodes),
            assigned_count=sum(1 for item in finalized_outcomes if item.status == "assigned"),
            unchanged_count=sum(
                1 for item in finalized_outcomes if item.status == "already_assigned"
            ),
            error_count=sum(1 for item in finalized_outcomes if item.status == "error"),
            selected_node_ids=[node.node_id for node in selected_nodes],
            outcomes=finalized_outcomes,
        )
