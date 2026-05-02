"""
Abstract: Adapter for taxonomy projection writes used by knowledge graph flows.
Out of scope: SQL persistence, Redis serialization, and taxonomy view response shaping.
"""

from __future__ import annotations

from typing import Protocol

from modules.taxonomy.dto import TaxonomyScopeIdentity


class TaxonomyProjectionRepoPort(Protocol):
    async def assign_node_to_root(self, *, node_id: int) -> int: ...

    async def list_taxonomy_node_ids_for_node_ids(
        self,
        *,
        node_ids: list[int],
    ) -> dict[int, int]: ...

    async def list_scope_identities_for_node_ids(
        self,
        *,
        node_ids: list[int],
    ) -> dict[int, TaxonomyScopeIdentity]: ...

    async def add_projected_edge_ids_for_scope(
        self,
        *,
        scope_identity: TaxonomyScopeIdentity,
        edge_ids: list[int],
    ) -> None: ...


class TaxonomyProjectionPortAdapter:
    def __init__(self, *, repo: TaxonomyProjectionRepoPort) -> None:
        self._repo = repo

    async def assign_node_to_root(self, *, node_id: int) -> int:
        return await self._repo.assign_node_to_root(node_id=node_id)

    async def list_taxonomy_node_ids_for_node_ids(self, *, node_ids: list[int]) -> dict[int, int]:
        return await self._repo.list_taxonomy_node_ids_for_node_ids(node_ids=node_ids)

    async def list_scope_identities_for_node_ids(
        self,
        *,
        node_ids: list[int],
    ) -> dict[int, TaxonomyScopeIdentity]:
        return await self._repo.list_scope_identities_for_node_ids(node_ids=node_ids)

    async def add_projected_edge_ids_for_scope(
        self,
        *,
        scope_identity: TaxonomyScopeIdentity,
        edge_ids: list[int],
    ) -> None:
        await self._repo.add_projected_edge_ids_for_scope(
            scope_identity=scope_identity,
            edge_ids=edge_ids,
        )
