"""
Abstract: Taxonomy service boundary for tree reads and final assignment persistence.
Out of scope: HTTP endpoint wiring and LLM classification orchestration.
"""

from __future__ import annotations

from datetime import datetime
from typing import Protocol

from modules.taxonomy.dto import TaxonomyAssignmentRecord, TaxonomyNodeRecord, TaxonomyTreeNode


class TaxonomyRepoProtocol(Protocol):
    async def list_tree_nodes(self) -> list[TaxonomyNodeRecord]: ...

    async def list_children(self, *, parent_id: int | None) -> list[TaxonomyNodeRecord]: ...

    async def get_assignment_for_node(self, *, node_id: int) -> TaxonomyAssignmentRecord | None: ...

    async def set_final_assignment(
        self,
        *,
        node_id: int,
        taxonomy_node_id: int,
        assigned_at: datetime,
    ) -> TaxonomyAssignmentRecord: ...

    async def commit(self) -> None: ...

    async def rollback(self) -> None: ...


class TaxonomyService:
    def __init__(self, *, repo: TaxonomyRepoProtocol) -> None:
        self._repo = repo

    async def list_tree(self) -> list[TaxonomyTreeNode]:
        records = await self._repo.list_tree_nodes()
        tree_nodes_by_id: dict[int, TaxonomyTreeNode] = {}
        roots: list[TaxonomyTreeNode] = []

        for record in records:
            tree_node = TaxonomyTreeNode(
                id=record.id,
                parent_id=record.parent_id,
                name=record.name,
                depth=record.depth,
                is_leaf=record.is_leaf,
            )
            tree_nodes_by_id[record.id] = tree_node
            if record.parent_id is None:
                roots.append(tree_node)
                continue
            tree_nodes_by_id[record.parent_id].children.append(tree_node)

        return roots

    async def list_children(self, *, parent_id: int | None) -> list[TaxonomyNodeRecord]:
        return await self._repo.list_children(parent_id=parent_id)

    async def get_assignment_for_node(self, *, node_id: int) -> TaxonomyAssignmentRecord | None:
        return await self._repo.get_assignment_for_node(node_id=node_id)

    async def set_final_assignment(
        self,
        *,
        node_id: int,
        taxonomy_node_id: int,
        assigned_at: datetime,
    ) -> TaxonomyAssignmentRecord:
        try:
            assignment = await self._repo.set_final_assignment(
                node_id=node_id,
                taxonomy_node_id=taxonomy_node_id,
                assigned_at=assigned_at,
            )
            await self._repo.commit()
            return assignment
        except Exception:
            await self._repo.rollback()
            raise
