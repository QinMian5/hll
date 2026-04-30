"""
Abstract: Unit tests for taxonomy service tree assembly and assignment orchestration.
Out of scope: SQL query details, trigger enforcement, and HTTP transport.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

import pytest

from core.errors import ApplicationError, DomainError, ErrorCode
from modules.knowledge_graph.dto import ProjectionCardNode, ProjectionCardTitle, ProjectionEdge
from modules.taxonomy.dto import (
    TaxonomyAssignmentRecord,
    TaxonomyLeafAssignment,
    TaxonomyLeafAssignmentCount,
    TaxonomyNodeRecord,
)
from modules.taxonomy.schema import (
    TaxonomyNodeBranchViewResponse,
    TaxonomyNodeLeafViewResponse,
    TaxonomyRootViewResponse,
)
from modules.taxonomy.service import TaxonomyService


@dataclass(slots=True)
class _StubRepo:
    tree_nodes: list[TaxonomyNodeRecord] = field(default_factory=list)
    children: list[TaxonomyNodeRecord] = field(default_factory=list)
    assignment: TaxonomyAssignmentRecord | None = None
    assigned_leaf_assignments: list[TaxonomyLeafAssignment] = field(default_factory=list)
    assigned_leaf_counts: list[TaxonomyLeafAssignmentCount] = field(default_factory=list)
    assigned_leaf_node_ids: list[int] = field(default_factory=list)
    projected_edge_ids: list[int] = field(default_factory=list)
    set_result: TaxonomyAssignmentRecord | None = None
    committed: bool = False
    rolled_back: bool = False
    fail_on_set: bool = False
    list_final_assignments_called: bool = False
    list_leaf_assignment_counts_called: bool = False
    list_assigned_node_ids_for_leaf_called_with: list[int] = field(default_factory=list)
    list_projected_edge_ids_for_leaf_called_with: list[int] = field(default_factory=list)
    add_projected_edge_batches: list[tuple[int, list[int]]] = field(default_factory=list)
    cleared_projected_leaf_ids: list[int] = field(default_factory=list)
    leaf_lookup_by_node_id: dict[int, int] = field(default_factory=dict)

    async def list_tree_nodes(self) -> list[TaxonomyNodeRecord]:
        return list(self.tree_nodes)

    async def get_node_by_id(self, *, node_id: int) -> TaxonomyNodeRecord | None:
        for node in self.tree_nodes:
            if node.id == node_id:
                return node
        return None

    async def list_children(self, *, parent_id: int | None) -> list[TaxonomyNodeRecord]:
        assert parent_id == 1
        return list(self.children)

    async def get_assignment_for_node(self, *, node_id: int) -> TaxonomyAssignmentRecord | None:
        assert node_id == 41
        return self.assignment

    async def list_final_assignments(self) -> list[TaxonomyLeafAssignment]:
        self.list_final_assignments_called = True
        return list(self.assigned_leaf_assignments)

    async def list_leaf_assignment_counts(self) -> list[TaxonomyLeafAssignmentCount]:
        self.list_leaf_assignment_counts_called = True
        return list(self.assigned_leaf_counts)

    async def list_assigned_node_ids_for_leaf(self, *, leaf_id: int) -> list[int]:
        self.list_assigned_node_ids_for_leaf_called_with.append(leaf_id)
        return list(self.assigned_leaf_node_ids)

    async def list_projected_edge_ids_for_leaf(self, *, leaf_id: int) -> list[int]:
        self.list_projected_edge_ids_for_leaf_called_with.append(leaf_id)
        return list(self.projected_edge_ids)

    async def add_projected_edge_ids_for_leaf(self, *, leaf_id: int, edge_ids: list[int]) -> None:
        self.add_projected_edge_batches.append((leaf_id, list(edge_ids)))

    async def clear_projected_edge_ids_for_leaf(self, *, leaf_id: int) -> None:
        self.cleared_projected_leaf_ids.append(leaf_id)

    async def list_leaf_ids_for_node_ids(self, *, node_ids: list[int]) -> dict[int, int]:
        return {
            node_id: self.leaf_lookup_by_node_id[node_id]
            for node_id in node_ids
            if node_id in self.leaf_lookup_by_node_id
        }

    async def set_current_assignment(
        self,
        *,
        node_id: int,
        taxonomy_node_id: int,
    ) -> TaxonomyAssignmentRecord:
        assert node_id == 41
        assert taxonomy_node_id == 9
        if self.fail_on_set:
            raise RuntimeError("assignment write failed")
        assert self.set_result is not None
        return self.set_result

    async def assign_node_to_root_unclassified(self, *, node_id: int) -> int:
        assert node_id == 41
        return 9

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        self.rolled_back = True


@dataclass(slots=True)
class _StubProjectionPort:
    nodes: list[ProjectionCardNode]
    edges: list[ProjectionEdge]
    card_request_batches: list[list[int]] = field(default_factory=list)
    title_request_batches: list[list[int]] = field(default_factory=list)
    edge_id_request_batches: list[list[int]] = field(default_factory=list)
    adjacent_edge_id_request_batches: list[list[int]] = field(default_factory=list)
    adjacent_edge_ids: list[int] = field(default_factory=list)

    async def list_projection_cards_for_node_ids(
        self,
        *,
        node_ids: list[int],
    ) -> list[ProjectionCardNode]:
        self.card_request_batches.append(list(node_ids))
        node_id_set = set(node_ids)
        return [node for node in self.nodes if node.node_id in node_id_set]

    async def list_projection_card_titles_for_node_ids(
        self,
        *,
        node_ids: list[int],
    ) -> list[ProjectionCardTitle]:
        self.title_request_batches.append(list(node_ids))
        node_id_set = set(node_ids)
        return [
            ProjectionCardTitle(node_id=node.node_id, title=node.title)
            for node in self.nodes
            if node.node_id in node_id_set
        ]

    async def list_projection_edges_for_edge_ids(
        self,
        *,
        edge_ids: list[int],
    ) -> list[ProjectionEdge]:
        self.edge_id_request_batches.append(list(edge_ids))
        return list(self.edges[: len(edge_ids)])

    async def list_adjacent_edge_ids_for_node_ids(
        self,
        *,
        node_ids: list[int],
    ) -> list[int]:
        self.adjacent_edge_id_request_batches.append(list(node_ids))
        return list(self.adjacent_edge_ids)


@dataclass(slots=True)
class _StubViewCache:
    descendant_counts: dict[int, int] | None = None
    stored_descendant_counts: dict[int, int] | None = None
    lock_acquired: bool = False
    get_descendant_counts_called: bool = False
    set_descendant_counts_called: bool = False
    acquire_descendant_counts_lock_called: bool = False
    invalidated_leaf_layout_ids: list[int] = field(default_factory=list)

    async def get_descendant_counts(self) -> dict[int, int] | None:
        self.get_descendant_counts_called = True
        return self.descendant_counts

    async def set_descendant_counts(self, counts: dict[int, int]) -> None:
        self.set_descendant_counts_called = True
        self.stored_descendant_counts = dict(counts)

    async def acquire_descendant_counts_lock(self) -> bool:
        self.acquire_descendant_counts_lock_called = True
        return self.lock_acquired

    async def invalidate_leaf_layout(self, *, leaf_id: int) -> None:
        self.invalidated_leaf_layout_ids.append(leaf_id)


def _leaf_assignment() -> TaxonomyAssignmentRecord:
    return TaxonomyAssignmentRecord(
        id=7,
        node_id=41,
        taxonomy_node=TaxonomyNodeRecord(
            id=9,
            parent_id=2,
            name="General",
            depth=2,
            is_leaf=True,
        ),
        assigned_at=datetime(2026, 4, 5, 3, 0, tzinfo=UTC),
    )


@pytest.mark.anyio
async def test_list_tree_builds_nested_nodes_from_repo_records() -> None:
    service = TaxonomyService(
        repo=_StubRepo(
            tree_nodes=[
                TaxonomyNodeRecord(id=1, parent_id=None, name="Science", depth=0, is_leaf=False),
                TaxonomyNodeRecord(id=2, parent_id=1, name="Mathematics", depth=1, is_leaf=False),
                TaxonomyNodeRecord(id=3, parent_id=2, name="Algebra", depth=2, is_leaf=True),
                TaxonomyNodeRecord(id=4, parent_id=1, name="Physics", depth=1, is_leaf=True),
            ]
        )
    )

    tree = await service.list_tree()

    assert [node.name for node in tree] == ["Science"]
    assert [node.name for node in tree[0].children] == ["Mathematics", "Physics"]
    assert [node.name for node in tree[0].children[0].children] == ["Algebra"]


@pytest.mark.anyio
async def test_list_children_returns_repo_ordered_children() -> None:
    service = TaxonomyService(
        repo=_StubRepo(
            children=[
                TaxonomyNodeRecord(id=5, parent_id=1, name="Chemistry", depth=1, is_leaf=True),
                TaxonomyNodeRecord(id=6, parent_id=1, name="Physics", depth=1, is_leaf=True),
            ]
        )
    )

    children = await service.list_children(parent_id=1)

    assert [child.name for child in children] == ["Chemistry", "Physics"]


@pytest.mark.anyio
async def test_get_assignment_for_node_returns_leaf_assignment() -> None:
    service = TaxonomyService(repo=_StubRepo(assignment=_leaf_assignment()))

    assignment = await service.get_assignment_for_node(node_id=41)

    assert assignment is not None
    assert assignment.taxonomy_node.name == "General"


@pytest.mark.anyio
async def test_set_current_assignment_commits_written_assignment() -> None:
    repo = _StubRepo(set_result=_leaf_assignment(), assigned_leaf_node_ids=[41])
    projection_port = _StubProjectionPort(nodes=[], edges=[], adjacent_edge_ids=[71, 72])
    service = TaxonomyService(repo=repo, knowledge_projection_port=projection_port)

    assignment = await service.set_current_assignment(
        node_id=41,
        taxonomy_node_id=9,
    )

    assert assignment.taxonomy_node.id == 9
    assert projection_port.adjacent_edge_id_request_batches == [[41]]
    assert repo.add_projected_edge_batches == [(9, [71, 72])]
    assert repo.committed is True
    assert repo.rolled_back is False


@pytest.mark.anyio
async def test_set_current_assignment_invalidates_refreshed_leaf_layouts() -> None:
    previous_assignment = TaxonomyAssignmentRecord(
        id=7,
        node_id=41,
        taxonomy_node=TaxonomyNodeRecord(
            id=4,
            parent_id=2,
            name="Old",
            depth=2,
            is_leaf=True,
        ),
        assigned_at=datetime(2026, 4, 5, 3, 0, tzinfo=UTC),
    )
    repo = _StubRepo(
        assignment=previous_assignment,
        set_result=_leaf_assignment(),
        assigned_leaf_node_ids=[41],
    )
    cache = _StubViewCache()
    projection_port = _StubProjectionPort(nodes=[], edges=[], adjacent_edge_ids=[71, 72])
    service = TaxonomyService(
        repo=repo,
        knowledge_projection_port=projection_port,
        view_cache=cache,
    )

    await service.set_current_assignment(
        node_id=41,
        taxonomy_node_id=9,
    )

    assert repo.cleared_projected_leaf_ids == [4, 9]
    assert cache.invalidated_leaf_layout_ids == [4, 9]


@pytest.mark.anyio
async def test_set_current_assignment_rolls_back_and_reraises() -> None:
    repo = _StubRepo(fail_on_set=True)
    service = TaxonomyService(repo=repo)

    with pytest.raises(RuntimeError, match="assignment write failed"):
        await service.set_current_assignment(
            node_id=41,
            taxonomy_node_id=9,
        )

    assert repo.committed is False
    assert repo.rolled_back is True


@pytest.mark.anyio
async def test_get_root_view_omits_children_without_descendant_cards() -> None:
    repo = _StubRepo(
        tree_nodes=[
            TaxonomyNodeRecord(id=1, parent_id=None, name="Root", depth=0, is_leaf=False),
            TaxonomyNodeRecord(id=2, parent_id=1, name="Science", depth=1, is_leaf=False),
            TaxonomyNodeRecord(id=3, parent_id=1, name="Unclassified", depth=1, is_leaf=True),
            TaxonomyNodeRecord(id=4, parent_id=2, name="Unclassified", depth=2, is_leaf=True),
        ],
        assigned_leaf_assignments=[
            TaxonomyLeafAssignment(node_id=11, taxonomy_leaf_id=4),
        ],
        assigned_leaf_counts=[
            TaxonomyLeafAssignmentCount(taxonomy_leaf_id=4, card_count=1),
        ],
    )
    service = TaxonomyService(repo=repo)

    view = await service.get_root_view()

    assert isinstance(view, TaxonomyRootViewResponse)
    assert view.breadcrumb == []
    assert [child.id for child in view.children] == [2]
    assert [child.descendant_card_count for child in view.children] == [1]
    assert repo.list_leaf_assignment_counts_called is True
    assert repo.list_final_assignments_called is False


@pytest.mark.anyio
async def test_get_node_view_returns_branch_shape_for_non_leaf() -> None:
    repo = _StubRepo(
        tree_nodes=[
            TaxonomyNodeRecord(id=1, parent_id=None, name="Root", depth=0, is_leaf=False),
            TaxonomyNodeRecord(id=2, parent_id=1, name="A", depth=1, is_leaf=False),
            TaxonomyNodeRecord(id=3, parent_id=1, name="B", depth=1, is_leaf=True),
            TaxonomyNodeRecord(id=4, parent_id=2, name="A1", depth=2, is_leaf=True),
        ],
        assigned_leaf_assignments=[
            TaxonomyLeafAssignment(node_id=21, taxonomy_leaf_id=3),
            TaxonomyLeafAssignment(node_id=22, taxonomy_leaf_id=4),
        ],
        assigned_leaf_counts=[
            TaxonomyLeafAssignmentCount(taxonomy_leaf_id=3, card_count=1),
            TaxonomyLeafAssignmentCount(taxonomy_leaf_id=4, card_count=1),
        ],
    )
    service = TaxonomyService(repo=repo)

    view = await service.get_node_view(node_id=1)

    assert isinstance(view, TaxonomyNodeBranchViewResponse)
    assert view.node_kind == "branch"
    assert [item.id for item in view.breadcrumb] == [1]
    assert [child.id for child in view.children] == [2, 3]


@pytest.mark.anyio
async def test_get_node_view_omits_empty_branch_children() -> None:
    repo = _StubRepo(
        tree_nodes=[
            TaxonomyNodeRecord(id=1, parent_id=None, name="Root", depth=0, is_leaf=False),
            TaxonomyNodeRecord(id=2, parent_id=1, name="A", depth=1, is_leaf=False),
            TaxonomyNodeRecord(id=3, parent_id=1, name="B", depth=1, is_leaf=True),
            TaxonomyNodeRecord(id=4, parent_id=2, name="A1", depth=2, is_leaf=True),
        ],
        assigned_leaf_assignments=[
            TaxonomyLeafAssignment(node_id=22, taxonomy_leaf_id=4),
        ],
        assigned_leaf_counts=[
            TaxonomyLeafAssignmentCount(taxonomy_leaf_id=4, card_count=1),
        ],
    )
    service = TaxonomyService(repo=repo)

    view = await service.get_node_view(node_id=1)

    assert isinstance(view, TaxonomyNodeBranchViewResponse)
    assert [child.id for child in view.children] == [2]
    assert [child.descendant_card_count for child in view.children] == [1]


@pytest.mark.anyio
async def test_get_root_view_uses_cached_descendant_counts_when_available() -> None:
    repo = _StubRepo(
        tree_nodes=[
            TaxonomyNodeRecord(id=1, parent_id=None, name="Root", depth=0, is_leaf=False),
            TaxonomyNodeRecord(id=2, parent_id=1, name="Science", depth=1, is_leaf=False),
            TaxonomyNodeRecord(id=3, parent_id=1, name="Unclassified", depth=1, is_leaf=True),
        ],
    )
    cache = _StubViewCache(descendant_counts={1: 5, 2: 5, 3: 0})
    service = TaxonomyService(repo=repo, view_cache=cache)

    view = await service.get_root_view()

    assert [child.id for child in view.children] == [2]
    assert [child.descendant_card_count for child in view.children] == [5]
    assert cache.get_descendant_counts_called is True
    assert cache.acquire_descendant_counts_lock_called is False
    assert repo.list_leaf_assignment_counts_called is False
    assert repo.list_final_assignments_called is False


@pytest.mark.anyio
async def test_get_root_view_rebuilds_and_caches_descendant_counts_on_cache_miss() -> None:
    repo = _StubRepo(
        tree_nodes=[
            TaxonomyNodeRecord(id=1, parent_id=None, name="Root", depth=0, is_leaf=False),
            TaxonomyNodeRecord(id=2, parent_id=1, name="Science", depth=1, is_leaf=False),
            TaxonomyNodeRecord(id=4, parent_id=2, name="Unclassified", depth=2, is_leaf=True),
        ],
        assigned_leaf_counts=[
            TaxonomyLeafAssignmentCount(taxonomy_leaf_id=4, card_count=2),
        ],
    )
    cache = _StubViewCache(descendant_counts=None, lock_acquired=True)
    service = TaxonomyService(repo=repo, view_cache=cache)

    view = await service.get_root_view()

    assert [child.id for child in view.children] == [2]
    assert cache.acquire_descendant_counts_lock_called is True
    assert cache.stored_descendant_counts == {1: 2, 2: 2, 4: 2}
    assert repo.list_leaf_assignment_counts_called is True
    assert repo.list_final_assignments_called is False


@pytest.mark.anyio
async def test_get_node_view_returns_leaf_metadata_without_full_graph() -> None:
    repo = _StubRepo(
        tree_nodes=[
            TaxonomyNodeRecord(id=1, parent_id=None, name="Root", depth=0, is_leaf=False),
            TaxonomyNodeRecord(id=2, parent_id=1, name="Leaf", depth=1, is_leaf=True),
        ],
        assigned_leaf_node_ids=[11, 12],
        projected_edge_ids=[501, 502],
    )
    projection_port = _StubProjectionPort(
        nodes=[
            ProjectionCardNode(
                node_id=11,
                current_version=3,
                title="Inner 11",
                content="Inner 11 content",
            ),
            ProjectionCardNode(
                node_id=12,
                current_version=5,
                title="Inner 12",
                content="Inner 12 content",
            ),
            ProjectionCardNode(
                node_id=77,
                current_version=7,
                title="Outer 77",
                content="Outer 77 content",
            ),
        ],
        edges=[
            ProjectionEdge(node_a_id=11, node_b_id=12, strength=0.91),
            ProjectionEdge(node_a_id=12, node_b_id=77, strength=0.66),
        ],
    )
    service = TaxonomyService(repo=repo, knowledge_projection_port=projection_port)

    view = await service.get_node_view(node_id=2)

    assert isinstance(view, TaxonomyNodeLeafViewResponse)
    assert view.node_kind == "leaf"
    assert [item.id for item in view.breadcrumb] == [1, 2]
    assert view.layout_version == "taxonomy-leaf-layout-v2"
    assert view.world_bounds.min_x < 0.0
    assert view.world_bounds.min_y < 0.0
    assert view.world_bounds.max_x > 0.0
    assert view.world_bounds.max_y > 0.0
    assert view.node_count == 3
    assert view.edge_count == 2
    assert repo.list_assigned_node_ids_for_leaf_called_with == [2]
    assert repo.list_projected_edge_ids_for_leaf_called_with == [2]
    assert repo.list_final_assignments_called is False
    assert projection_port.edge_id_request_batches == [[501, 502]]
    assert projection_port.card_request_batches == []


@pytest.mark.anyio
async def test_get_leaf_layout_slice_returns_backend_coordinates_for_requested_bounds() -> None:
    repo = _StubRepo(
        tree_nodes=[
            TaxonomyNodeRecord(id=1, parent_id=None, name="Root", depth=0, is_leaf=False),
            TaxonomyNodeRecord(id=2, parent_id=1, name="Leaf", depth=1, is_leaf=True),
        ],
        assigned_leaf_node_ids=[11, 12],
        projected_edge_ids=[501, 502],
    )
    projection_port = _StubProjectionPort(
        nodes=[],
        edges=[
            ProjectionEdge(node_a_id=11, node_b_id=12, strength=0.91),
            ProjectionEdge(node_a_id=12, node_b_id=77, strength=0.66),
        ],
    )
    service = TaxonomyService(repo=repo, knowledge_projection_port=projection_port)

    layout_slice = await service.get_leaf_layout_slice(
        node_id=2,
        min_x=-1000.0,
        min_y=-1000.0,
        max_x=1000.0,
        max_y=1000.0,
    )

    assert layout_slice.leaf_id == 2
    assert [(node.id, node.scope) for node in layout_slice.nodes] == [
        (11, "inner"),
        (12, "inner"),
        (77, "outer"),
    ]
    assert all(node.x != 0.0 or node.y != 0.0 for node in layout_slice.nodes)
    assert layout_slice.edges == [(11, 12, 0.91), (12, 77, 0.66)]


@pytest.mark.anyio
async def test_get_node_view_raises_not_found_for_unknown_node_id() -> None:
    repo = _StubRepo(
        tree_nodes=[
            TaxonomyNodeRecord(id=1, parent_id=None, name="Root", depth=0, is_leaf=False),
        ]
    )
    service = TaxonomyService(repo=repo)

    with pytest.raises(DomainError) as exc_info:
        await service.get_node_view(node_id=999)

    assert exc_info.value.code == ErrorCode.DOMAIN_TAXONOMY_RESOURCE_NOT_FOUND


@pytest.mark.anyio
async def test_get_leaf_node_details_returns_requested_records_in_request_order() -> None:
    repo = _StubRepo(
        tree_nodes=[
            TaxonomyNodeRecord(id=1, parent_id=None, name="Root", depth=0, is_leaf=False),
            TaxonomyNodeRecord(id=2, parent_id=1, name="Leaf", depth=1, is_leaf=True),
        ],
        assigned_leaf_node_ids=[11, 12],
        projected_edge_ids=[501, 502],
    )
    projection_port = _StubProjectionPort(
        nodes=[
            ProjectionCardNode(
                node_id=11,
                current_version=3,
                title="Inner 11",
                content="Inner 11 content",
            ),
            ProjectionCardNode(
                node_id=12,
                current_version=5,
                title="Inner 12",
                content="Inner 12 content",
            ),
            ProjectionCardNode(
                node_id=77,
                current_version=7,
                title="Outer 77",
                content="Outer 77 content",
            ),
        ],
        edges=[
            ProjectionEdge(node_a_id=11, node_b_id=12, strength=0.91),
            ProjectionEdge(node_a_id=12, node_b_id=77, strength=0.66),
        ],
    )
    service = TaxonomyService(repo=repo, knowledge_projection_port=projection_port)

    detail_response = await service.get_leaf_node_details(node_id=2, node_ids=[77, 11])  # type: ignore[attr-defined]

    assert [node.model_dump() for node in detail_response.nodes] == [
        {
            "id": 77,
            "current_version": 7,
            "title": "Outer 77",
            "content": "Outer 77 content",
        },
        {
            "id": 11,
            "current_version": 3,
            "title": "Inner 11",
            "content": "Inner 11 content",
        },
    ]
    assert repo.list_assigned_node_ids_for_leaf_called_with == [2]
    assert repo.list_projected_edge_ids_for_leaf_called_with == [2]
    assert repo.list_final_assignments_called is False
    assert projection_port.edge_id_request_batches == [[501, 502]]
    assert projection_port.card_request_batches == [[77, 11]]
    assert projection_port.title_request_batches == []


@pytest.mark.anyio
async def test_get_leaf_node_titles_returns_requested_titles_without_content() -> None:
    repo = _StubRepo(
        tree_nodes=[
            TaxonomyNodeRecord(id=1, parent_id=None, name="Root", depth=0, is_leaf=False),
            TaxonomyNodeRecord(id=2, parent_id=1, name="Leaf", depth=1, is_leaf=True),
        ],
        assigned_leaf_node_ids=[11, 12],
        projected_edge_ids=[501, 502],
    )
    projection_port = _StubProjectionPort(
        nodes=[
            ProjectionCardNode(
                node_id=11,
                current_version=3,
                title="Inner 11",
                content="Inner 11 content",
            ),
            ProjectionCardNode(
                node_id=12,
                current_version=5,
                title="Inner 12",
                content="Inner 12 content",
            ),
            ProjectionCardNode(
                node_id=77,
                current_version=7,
                title="Outer 77",
                content="Outer 77 content",
            ),
        ],
        edges=[
            ProjectionEdge(node_a_id=11, node_b_id=12, strength=0.91),
            ProjectionEdge(node_a_id=12, node_b_id=77, strength=0.66),
        ],
    )
    service = TaxonomyService(repo=repo, knowledge_projection_port=projection_port)

    title_response = await service.get_leaf_node_titles(node_id=2, node_ids=[77, 11])  # type: ignore[attr-defined]

    assert [node.model_dump() for node in title_response.nodes] == [
        {
            "id": 77,
            "title": "Outer 77",
        },
        {
            "id": 11,
            "title": "Inner 11",
        },
    ]
    assert repo.list_assigned_node_ids_for_leaf_called_with == [2]
    assert repo.list_projected_edge_ids_for_leaf_called_with == [2]
    assert repo.list_final_assignments_called is False
    assert projection_port.edge_id_request_batches == [[501, 502]]
    assert projection_port.card_request_batches == []
    assert projection_port.title_request_batches == [[77, 11]]


@pytest.mark.anyio
async def test_get_leaf_node_details_rejects_non_leaf_taxonomy_node() -> None:
    repo = _StubRepo(
        tree_nodes=[
            TaxonomyNodeRecord(id=1, parent_id=None, name="Root", depth=0, is_leaf=False),
            TaxonomyNodeRecord(id=2, parent_id=1, name="Branch", depth=1, is_leaf=False),
            TaxonomyNodeRecord(id=3, parent_id=2, name="Leaf", depth=2, is_leaf=True),
        ],
        assigned_leaf_assignments=[
            TaxonomyLeafAssignment(node_id=11, taxonomy_leaf_id=3),
        ],
    )
    projection_port = _StubProjectionPort(nodes=[], edges=[])
    service = TaxonomyService(repo=repo, knowledge_projection_port=projection_port)

    with pytest.raises(ApplicationError) as exc_info:
        await service.get_leaf_node_details(node_id=2, node_ids=[11])  # type: ignore[attr-defined]

    assert exc_info.value.code == ErrorCode.APPLICATION_TAXONOMY_INPUT_INVALID


@pytest.mark.anyio
async def test_get_leaf_node_details_rejects_node_ids_outside_active_leaf_graph() -> None:
    repo = _StubRepo(
        tree_nodes=[
            TaxonomyNodeRecord(id=1, parent_id=None, name="Root", depth=0, is_leaf=False),
            TaxonomyNodeRecord(id=2, parent_id=1, name="Leaf", depth=1, is_leaf=True),
        ],
        assigned_leaf_node_ids=[11],
        projected_edge_ids=[901],
    )
    projection_port = _StubProjectionPort(
        nodes=[
            ProjectionCardNode(
                node_id=11,
                current_version=3,
                title="Inner 11",
                content="Inner 11 content",
            ),
            ProjectionCardNode(
                node_id=77,
                current_version=7,
                title="Outer 77",
                content="Outer 77 content",
            ),
        ],
        edges=[
            ProjectionEdge(node_a_id=11, node_b_id=77, strength=0.66),
        ],
    )
    service = TaxonomyService(repo=repo, knowledge_projection_port=projection_port)

    with pytest.raises(ApplicationError) as exc_info:
        await service.get_leaf_node_details(node_id=2, node_ids=[999])  # type: ignore[attr-defined]

    assert exc_info.value.code == ErrorCode.APPLICATION_TAXONOMY_INPUT_INVALID
