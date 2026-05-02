"""
Abstract: Business-layer backfill for assigning historical unassigned cards to Root.
Out of scope: CLI parsing, migration execution, and live job-queue classification.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol

from modules.taxonomy.dto import TaxonomyAssignmentCount, TaxonomyNodeRecord, TaxonomyScopeIdentity
from modules.taxonomy.projection_rebuild import (
    TaxonomyScopeProjectionRebuildKnowledgePort,
    rebuild_taxonomy_scope_projection_edges,
)


@dataclass(slots=True, frozen=True)
class TaxonomyRootAssignmentBackfillResult:
    mode: Literal["dry-run", "apply"]
    root_id: int | None
    total_cards: int
    assigned_before: int
    missing_before: int
    inserted_assignments: int
    missing_after: int
    projection_rebuilt: bool


class TaxonomyRootAssignmentBackfillRepoPort(Protocol):
    async def get_root_node(self) -> TaxonomyNodeRecord | None: ...

    async def ensure_root(self) -> TaxonomyNodeRecord: ...

    async def count_nodes(self) -> int: ...

    async def count_taxonomy_assignments(self) -> int: ...

    async def count_nodes_missing_taxonomy_assignment(self) -> int: ...

    async def assign_unassigned_nodes_to_taxonomy_node(self, *, taxonomy_node_id: int) -> None: ...

    async def list_tree_nodes(self) -> list[TaxonomyNodeRecord]: ...

    async def list_assignment_counts(self) -> list[TaxonomyAssignmentCount]: ...

    async def list_assigned_node_ids_for_scope(
        self,
        *,
        scope_identity: TaxonomyScopeIdentity,
    ) -> list[int]: ...

    async def clear_all_projected_edge_ids(self) -> None: ...

    async def add_projected_edge_ids_for_scope(
        self,
        *,
        scope_identity: TaxonomyScopeIdentity,
        edge_ids: list[int],
    ) -> None: ...

    async def commit(self) -> None: ...

    async def rollback(self) -> None: ...


class TaxonomyRootAssignmentBackfillService:
    def __init__(
        self,
        *,
        repo: TaxonomyRootAssignmentBackfillRepoPort,
        knowledge_projection_port: TaxonomyScopeProjectionRebuildKnowledgePort | None = None,
    ) -> None:
        self._repo = repo
        self._knowledge_projection_port = knowledge_projection_port

    async def run(self, *, apply: bool) -> TaxonomyRootAssignmentBackfillResult:
        if not apply:
            return await self._dry_run()
        return await self._apply()

    async def _dry_run(self) -> TaxonomyRootAssignmentBackfillResult:
        root = await self._repo.get_root_node()
        total_cards = await self._repo.count_nodes()
        assigned_before = await self._repo.count_taxonomy_assignments()
        missing_before = await self._repo.count_nodes_missing_taxonomy_assignment()
        return TaxonomyRootAssignmentBackfillResult(
            mode="dry-run",
            root_id=None if root is None else root.id,
            total_cards=total_cards,
            assigned_before=assigned_before,
            missing_before=missing_before,
            inserted_assignments=0,
            missing_after=missing_before,
            projection_rebuilt=False,
        )

    async def _apply(self) -> TaxonomyRootAssignmentBackfillResult:
        try:
            total_cards = await self._repo.count_nodes()
            assigned_before = await self._repo.count_taxonomy_assignments()
            missing_before = await self._repo.count_nodes_missing_taxonomy_assignment()
            root = await self._repo.ensure_root()
            if missing_before > 0:
                await self._repo.assign_unassigned_nodes_to_taxonomy_node(
                    taxonomy_node_id=root.id,
                )
            missing_after = await self._repo.count_nodes_missing_taxonomy_assignment()
            inserted_assignments = max(missing_before - missing_after, 0)
            projection_rebuilt = False
            if self._knowledge_projection_port is not None:
                await rebuild_taxonomy_scope_projection_edges(
                    repo=self._repo,
                    projection_port=self._knowledge_projection_port,
                )
                projection_rebuilt = True
            await self._repo.commit()
            return TaxonomyRootAssignmentBackfillResult(
                mode="apply",
                root_id=root.id,
                total_cards=total_cards,
                assigned_before=assigned_before,
                missing_before=missing_before,
                inserted_assignments=inserted_assignments,
                missing_after=missing_after,
                projection_rebuilt=projection_rebuilt,
            )
        except Exception:
            await self._repo.rollback()
            raise


__all__ = [
    "TaxonomyRootAssignmentBackfillResult",
    "TaxonomyRootAssignmentBackfillService",
]
