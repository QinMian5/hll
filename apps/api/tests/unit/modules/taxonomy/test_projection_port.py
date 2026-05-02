"""
Abstract: Unit tests for taxonomy projection adapter behavior.
Out of scope: SQL repository behavior and Redis cache serialization.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from modules.taxonomy.dto import TaxonomyScopeIdentity
from modules.taxonomy.projection_port import TaxonomyProjectionPortAdapter


@dataclass(slots=True)
class _StubProjectionRepo:
    assigned_taxonomy_node_id: int = 1
    add_calls: list[tuple[TaxonomyScopeIdentity, list[int]]] = field(default_factory=list)
    assigned_node_ids: list[int] = field(default_factory=list)
    taxonomy_lookup_by_node_id: dict[int, int] = field(default_factory=lambda: {11: 9, 12: 4})
    scope_lookup_by_node_id: dict[int, TaxonomyScopeIdentity] = field(
        default_factory=lambda: {
            11: TaxonomyScopeIdentity(scope_kind="virtual_unclassified", taxonomy_node_id=9),
            12: TaxonomyScopeIdentity(scope_kind="taxonomy_node", taxonomy_node_id=4),
        }
    )

    async def assign_node_to_root(self, *, node_id: int) -> int:
        self.assigned_node_ids.append(node_id)
        return self.assigned_taxonomy_node_id

    async def list_taxonomy_node_ids_for_node_ids(self, *, node_ids: list[int]) -> dict[int, int]:
        return {
            node_id: self.taxonomy_lookup_by_node_id[node_id]
            for node_id in node_ids
            if node_id in self.taxonomy_lookup_by_node_id
        }

    async def list_scope_identities_for_node_ids(
        self,
        *,
        node_ids: list[int],
    ) -> dict[int, TaxonomyScopeIdentity]:
        return {
            node_id: self.scope_lookup_by_node_id[node_id]
            for node_id in node_ids
            if node_id in self.scope_lookup_by_node_id
        }

    async def add_projected_edge_ids_for_scope(
        self,
        *,
        scope_identity: TaxonomyScopeIdentity,
        edge_ids: list[int],
    ) -> None:
        self.add_calls.append((scope_identity, list(edge_ids)))


@pytest.mark.anyio
async def test_assignment_to_root_delegates_without_cache_invalidation() -> None:
    repo = _StubProjectionRepo(assigned_taxonomy_node_id=1)
    port = TaxonomyProjectionPortAdapter(repo=repo)

    taxonomy_node_id = await port.assign_node_to_root(node_id=41)

    assert taxonomy_node_id == 1
    assert repo.assigned_node_ids == [41]


@pytest.mark.anyio
async def test_projected_edge_insert_delegates_without_cache_invalidation() -> None:
    repo = _StubProjectionRepo()
    port = TaxonomyProjectionPortAdapter(repo=repo)
    scope_identity = TaxonomyScopeIdentity(scope_kind="virtual_unclassified", taxonomy_node_id=4)

    await port.add_projected_edge_ids_for_scope(
        scope_identity=scope_identity,
        edge_ids=[501, 502],
    )

    assert repo.add_calls == [(scope_identity, [501, 502])]


@pytest.mark.anyio
async def test_assignment_lookup_delegates_without_invalidating_layout() -> None:
    repo = _StubProjectionRepo()
    port = TaxonomyProjectionPortAdapter(repo=repo)

    result = await port.list_taxonomy_node_ids_for_node_ids(node_ids=[12, 99, 11])

    assert result == {12: 4, 11: 9}


@pytest.mark.anyio
async def test_scope_lookup_delegates_without_invalidating_layout() -> None:
    repo = _StubProjectionRepo()
    port = TaxonomyProjectionPortAdapter(repo=repo)

    result = await port.list_scope_identities_for_node_ids(node_ids=[12, 99, 11])

    assert result == {
        12: TaxonomyScopeIdentity(scope_kind="taxonomy_node", taxonomy_node_id=4),
        11: TaxonomyScopeIdentity(scope_kind="virtual_unclassified", taxonomy_node_id=9),
    }
