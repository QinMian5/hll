"""
Abstract: Adapter for taxonomy projection writes used by knowledge graph flows.
Out of scope: SQL persistence, Redis serialization, and taxonomy view response shaping.
"""

from __future__ import annotations

from typing import Protocol


class TaxonomyProjectionRepoPort(Protocol):
    async def assign_node_to_root_unclassified(self, *, node_id: int) -> int: ...

    async def list_leaf_ids_for_node_ids(self, *, node_ids: list[int]) -> dict[int, int]: ...

    async def add_projected_edge_ids_for_leaf(
        self,
        *,
        leaf_id: int,
        edge_ids: list[int],
    ) -> None: ...


class TaxonomyProjectionPortAdapter:
    def __init__(self, *, repo: TaxonomyProjectionRepoPort) -> None:
        self._repo = repo

    async def assign_node_to_root_unclassified(self, *, node_id: int) -> int:
        return await self._repo.assign_node_to_root_unclassified(node_id=node_id)

    async def list_leaf_ids_for_node_ids(self, *, node_ids: list[int]) -> dict[int, int]:
        return await self._repo.list_leaf_ids_for_node_ids(node_ids=node_ids)

    async def add_projected_edge_ids_for_leaf(self, *, leaf_id: int, edge_ids: list[int]) -> None:
        await self._repo.add_projected_edge_ids_for_leaf(leaf_id=leaf_id, edge_ids=edge_ids)
