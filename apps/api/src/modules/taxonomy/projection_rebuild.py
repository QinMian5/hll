"""
Abstract: Rebuild helper for leaf-specific taxonomy edge projection rows.
Out of scope: CLI wiring, runtime scheduling, and migration execution.
"""

from __future__ import annotations

from typing import Protocol

from modules.taxonomy.dto import TaxonomyNodeRecord


class TaxonomyLeafProjectionRebuildRepoPort(Protocol):
    async def list_tree_nodes(self) -> list[TaxonomyNodeRecord]: ...

    async def list_assigned_node_ids_for_leaf(self, *, leaf_id: int) -> list[int]: ...

    async def clear_all_projected_edge_ids(self) -> None: ...

    async def add_projected_edge_ids_for_leaf(
        self,
        *,
        leaf_id: int,
        edge_ids: list[int],
    ) -> None: ...


class TaxonomyLeafProjectionRebuildKnowledgePort(Protocol):
    async def list_adjacent_edge_ids_for_node_ids(self, *, node_ids: list[int]) -> list[int]: ...


async def rebuild_taxonomy_leaf_projection_edges(
    *,
    repo: TaxonomyLeafProjectionRebuildRepoPort,
    projection_port: TaxonomyLeafProjectionRebuildKnowledgePort,
) -> None:
    tree_nodes = await repo.list_tree_nodes()
    leaf_ids = sorted(node.id for node in tree_nodes if node.is_leaf)

    await repo.clear_all_projected_edge_ids()
    for leaf_id in leaf_ids:
        inner_node_ids = await repo.list_assigned_node_ids_for_leaf(leaf_id=leaf_id)
        adjacent_edge_ids = await projection_port.list_adjacent_edge_ids_for_node_ids(
            node_ids=inner_node_ids
        )
        await repo.add_projected_edge_ids_for_leaf(
            leaf_id=leaf_id,
            edge_ids=adjacent_edge_ids,
        )
