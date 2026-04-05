"""
Abstract: Dependency contracts for taxonomy bootstrap import orchestration.
Out of scope: SQLAlchemy repository implementation and HTTP transport wiring.
"""

from __future__ import annotations

from typing import Protocol

from modules.taxonomy.dto import TaxonomyAssignmentRecord, TaxonomyNodeRecord


class TaxonomyImportPort(Protocol):
    async def has_any_taxonomy_nodes(self) -> bool: ...

    async def create_taxonomy_node(
        self,
        *,
        parent_id: int | None,
        name: str,
        depth: int,
        is_leaf: bool,
    ) -> int: ...

    async def commit(self) -> None: ...

    async def rollback(self) -> None: ...


class TaxonomyReadPort(Protocol):
    async def list_tree_nodes(self) -> list[TaxonomyNodeRecord]: ...

    async def list_children(self, *, parent_id: int | None) -> list[TaxonomyNodeRecord]: ...

    async def get_assignment_for_node(self, *, node_id: int) -> TaxonomyAssignmentRecord | None: ...

    async def list_assigned_leaf_depths_for_semantic_map(self) -> list[int]: ...

    async def list_assigned_node_ids_for_semantic_map(self) -> list[int]: ...
