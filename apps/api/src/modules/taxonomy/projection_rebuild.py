"""
Abstract: Rebuild helper for taxonomy card-scope edge projection rows.
Out of scope: CLI wiring, runtime scheduling, and migration execution.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Protocol

from modules.taxonomy.dto import TaxonomyAssignmentCount, TaxonomyNodeRecord, TaxonomyScopeIdentity
from modules.taxonomy.repo import TAXONOMY_NODE_SCOPE_KIND, VIRTUAL_UNCLASSIFIED_SCOPE_KIND


class TaxonomyScopeProjectionRebuildRepoPort(Protocol):
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


class TaxonomyScopeProjectionRebuildKnowledgePort(Protocol):
    async def list_adjacent_edge_ids_for_node_ids(self, *, node_ids: list[int]) -> list[int]: ...


async def rebuild_taxonomy_scope_projection_edges(
    *,
    repo: TaxonomyScopeProjectionRebuildRepoPort,
    projection_port: TaxonomyScopeProjectionRebuildKnowledgePort,
) -> None:
    tree_nodes = await repo.list_tree_nodes()
    scope_identities = _active_scope_identities(
        tree_nodes=tree_nodes,
        assignment_counts=await repo.list_assignment_counts(),
    )

    await repo.clear_all_projected_edge_ids()
    for scope_identity in scope_identities:
        inner_node_ids = await repo.list_assigned_node_ids_for_scope(scope_identity=scope_identity)
        adjacent_edge_ids = await projection_port.list_adjacent_edge_ids_for_node_ids(
            node_ids=inner_node_ids
        )
        await repo.add_projected_edge_ids_for_scope(
            scope_identity=scope_identity,
            edge_ids=adjacent_edge_ids,
        )


def _active_scope_identities(
    *,
    tree_nodes: list[TaxonomyNodeRecord],
    assignment_counts: list[TaxonomyAssignmentCount],
) -> list[TaxonomyScopeIdentity]:
    node_by_id = {node.id: node for node in tree_nodes}
    child_ids_by_parent: dict[int | None, list[int]] = defaultdict(list)
    for node in tree_nodes:
        child_ids_by_parent[node.parent_id].append(node.id)

    direct_counts = dict.fromkeys(node_by_id, 0)
    for count in assignment_counts:
        if count.taxonomy_node_id in direct_counts:
            direct_counts[count.taxonomy_node_id] = count.card_count

    descendant_counts = dict(direct_counts)
    for node in sorted(node_by_id.values(), key=lambda item: (item.depth, item.id), reverse=True):
        if node.parent_id is not None:
            descendant_counts[node.parent_id] += descendant_counts[node.id]

    identities: list[TaxonomyScopeIdentity] = []
    for node in sorted(node_by_id.values(), key=lambda item: (item.depth, item.name, item.id)):
        if direct_counts[node.id] <= 0:
            continue
        visible_child_ids = [
            child_id
            for child_id in child_ids_by_parent.get(node.id, [])
            if descendant_counts[child_id] > 0
        ]
        identities.append(
            TaxonomyScopeIdentity(
                scope_kind=(
                    VIRTUAL_UNCLASSIFIED_SCOPE_KIND
                    if visible_child_ids
                    else TAXONOMY_NODE_SCOPE_KIND
                ),
                taxonomy_node_id=node.id,
            )
        )
    return identities
