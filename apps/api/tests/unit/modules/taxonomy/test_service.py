"""
Abstract: Unit tests for taxonomy service tree assembly and assignment orchestration.
Out of scope: SQL query details, trigger enforcement, and HTTP transport.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime

import pytest

from core.errors import ApplicationError, ErrorCode
from modules.knowledge_graph.dto import ProjectionEdge
from modules.taxonomy import service as taxonomy_service_module
from modules.taxonomy.dto import (
    TaxonomyAssignmentCount,
    TaxonomyAssignmentRecord,
    TaxonomyCardScopeLayout,
    TaxonomyCardScopeLayoutComputeRequestState,
    TaxonomyCardScopeLayoutNode,
    TaxonomyCardScopeLayoutReadModel,
    TaxonomyCardScopePrecomputeTarget,
    TaxonomyCardScopeWorldBounds,
    TaxonomyNodeRecord,
    TaxonomyScopeIdentity,
)
from modules.taxonomy.repo import TAXONOMY_NODE_SCOPE_KIND, VIRTUAL_UNCLASSIFIED_SCOPE_KIND
from modules.taxonomy.service import TaxonomyService


@dataclass(slots=True)
class _StoredLayout:
    input_fingerprint: str
    layout: TaxonomyCardScopeLayout


@dataclass(slots=True)
class _StoredComputeRequest:
    input_fingerprint: str
    status: str
    last_error: str | None = None


@dataclass(slots=True)
class _StubRepo:
    tree_nodes: list[TaxonomyNodeRecord] = field(default_factory=list)
    assignment_counts: list[TaxonomyAssignmentCount] = field(default_factory=list)
    assigned_node_ids_by_scope: dict[tuple[str, int], list[int]] = field(default_factory=dict)
    projected_edge_ids: list[int] = field(default_factory=list)
    stored_layout: _StoredLayout | None = None
    compute_request: _StoredComputeRequest | None = None
    requested_layout_computes: list[tuple[TaxonomyScopeIdentity, str]] = field(default_factory=list)
    stored_layout_writes: list[tuple[TaxonomyScopeIdentity, str, TaxonomyCardScopeLayout]] = field(
        default_factory=list
    )
    scope_identity_by_node_id_calls: list[list[int]] = field(default_factory=list)
    scope_identity_results: list[dict[int, TaxonomyScopeIdentity]] = field(default_factory=list)
    cleared_scope_identities: list[TaxonomyScopeIdentity] = field(default_factory=list)
    added_scope_batches: list[tuple[TaxonomyScopeIdentity, list[int]]] = field(default_factory=list)
    set_result: TaxonomyAssignmentRecord | None = None
    committed: bool = False
    rolled_back: bool = False

    async def list_tree_nodes(self) -> list[TaxonomyNodeRecord]:
        return list(self.tree_nodes)

    async def get_node_by_id(self, *, node_id: int) -> TaxonomyNodeRecord | None:
        for node in self.tree_nodes:
            if node.id == node_id:
                return node
        return None

    async def list_children(self, *, parent_id: int | None) -> list[TaxonomyNodeRecord]:
        return [node for node in self.tree_nodes if node.parent_id == parent_id]

    async def get_assignment_for_node(self, *, node_id: int) -> TaxonomyAssignmentRecord | None:
        return None

    async def list_current_assignments(self) -> list[object]:
        return []

    async def list_assignment_counts(self) -> list[TaxonomyAssignmentCount]:
        return list(self.assignment_counts)

    async def list_assigned_node_ids_for_scope(
        self,
        *,
        scope_identity: TaxonomyScopeIdentity,
    ) -> list[int]:
        return list(
            self.assigned_node_ids_by_scope.get(
                (scope_identity.scope_kind, scope_identity.taxonomy_node_id),
                [],
            )
        )

    async def list_projected_edge_ids_for_scope(
        self,
        *,
        scope_identity: TaxonomyScopeIdentity,
    ) -> list[int]:
        return list(self.projected_edge_ids)

    async def get_card_scope_layout_read_model(
        self,
        *,
        scope_identity: TaxonomyScopeIdentity,
        layout_version: str,
    ) -> _StoredLayout | None:
        return self.stored_layout

    async def get_card_scope_layout_compute_request_state(
        self,
        *,
        scope_identity: TaxonomyScopeIdentity,
        layout_version: str,
    ) -> TaxonomyCardScopeLayoutComputeRequestState | None:
        if self.compute_request is None:
            return None
        return TaxonomyCardScopeLayoutComputeRequestState(
            input_fingerprint=self.compute_request.input_fingerprint,
            status=self.compute_request.status,
            last_error=self.compute_request.last_error,
        )

    async def upsert_card_scope_layout_read_model(
        self,
        *,
        scope_identity: TaxonomyScopeIdentity,
        input_fingerprint: str,
        layout: TaxonomyCardScopeLayout,
    ) -> None:
        self.stored_layout_writes.append((scope_identity, input_fingerprint, layout))
        self.stored_layout = _StoredLayout(input_fingerprint=input_fingerprint, layout=layout)

    async def request_card_scope_layout_compute(
        self,
        *,
        scope_identity: TaxonomyScopeIdentity,
        layout_version: str,
        input_fingerprint: str,
    ) -> bool:
        self.requested_layout_computes.append((scope_identity, input_fingerprint))
        self.compute_request = _StoredComputeRequest(
            input_fingerprint=input_fingerprint,
            status="pending",
        )
        return True

    async def add_projected_edge_ids_for_scope(
        self,
        *,
        scope_identity: TaxonomyScopeIdentity,
        edge_ids: list[int],
    ) -> None:
        self.added_scope_batches.append((scope_identity, list(edge_ids)))

    async def clear_projected_edge_ids_for_scope(
        self,
        *,
        scope_identity: TaxonomyScopeIdentity,
    ) -> None:
        self.cleared_scope_identities.append(scope_identity)

    async def list_taxonomy_node_ids_for_node_ids(self, *, node_ids: list[int]) -> dict[int, int]:
        return {}

    async def list_scope_identities_for_node_ids(
        self,
        *,
        node_ids: list[int],
    ) -> dict[int, TaxonomyScopeIdentity]:
        self.scope_identity_by_node_id_calls.append(list(node_ids))
        return self.scope_identity_results.pop(0)

    async def set_current_assignment(
        self,
        *,
        node_id: int,
        taxonomy_node_id: int,
    ) -> TaxonomyAssignmentRecord:
        assert self.set_result is not None
        return self.set_result

    async def assign_node_to_root(self, *, node_id: int) -> int:
        return 1

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        self.rolled_back = True


@dataclass(slots=True)
class _StubProjectionPort:
    adjacent_edge_ids: list[int] = field(default_factory=list)
    adjacent_requests: list[list[int]] = field(default_factory=list)

    async def list_projection_cards_for_node_ids(self, *, node_ids: list[int]) -> list[object]:
        return []

    async def list_projection_card_titles_for_node_ids(
        self,
        *,
        node_ids: list[int],
    ) -> list[object]:
        return []

    async def list_projection_edges_touching_node_ids(
        self,
        *,
        node_ids: list[int],
    ) -> list[ProjectionEdge]:
        return []

    async def list_projection_edges_for_edge_ids(
        self,
        *,
        edge_ids: list[int],
    ) -> list[ProjectionEdge]:
        return []

    async def list_adjacent_edge_ids_for_node_ids(self, *, node_ids: list[int]) -> list[int]:
        self.adjacent_requests.append(list(node_ids))
        return list(self.adjacent_edge_ids)


@dataclass(slots=True)
class _StubViewCache:
    layout: TaxonomyCardScopeLayout | None = None
    input_fingerprint: str = "cached-fingerprint"

    async def get_root_view(self) -> None:
        return None

    async def set_root_view(self, view: object) -> None:
        return None

    async def get_node_view(self, *, node_id: int) -> None:
        return None

    async def set_node_view(self, *, node_id: int, view: object) -> None:
        return None

    async def get_path_view(self, *, route_path: str) -> None:
        return None

    async def set_path_view(self, *, route_path: str, view: object) -> None:
        return None

    async def get_descendant_counts(self) -> None:
        return None

    async def set_descendant_counts(self, counts: dict[int, int]) -> None:
        return None

    async def acquire_descendant_counts_lock(self) -> bool:
        return True

    async def get_card_scope_layout(
        self,
        *,
        scope_identity: TaxonomyScopeIdentity,
    ) -> TaxonomyCardScopeLayoutReadModel | None:
        if self.layout is None:
            return None
        return TaxonomyCardScopeLayoutReadModel(
            input_fingerprint=self.input_fingerprint,
            layout=self.layout,
        )

    async def set_card_scope_layout(
        self,
        *,
        scope_identity: TaxonomyScopeIdentity,
        input_fingerprint: str,
        layout: TaxonomyCardScopeLayout,
    ) -> None:
        self.layout = layout
        self.input_fingerprint = input_fingerprint

    async def request_card_scope_layout_compute(
        self,
        *,
        scope_identity: TaxonomyScopeIdentity,
    ) -> bool:
        return True


def _tree() -> list[TaxonomyNodeRecord]:
    return [
        TaxonomyNodeRecord(id=1, parent_id=None, name="Root", route_slug="root", depth=0),
        TaxonomyNodeRecord(id=2, parent_id=1, name="Science", route_slug="science", depth=1),
    ]


def _layout() -> TaxonomyCardScopeLayout:
    return TaxonomyCardScopeLayout(
        layout_version="taxonomy-card-scope-layout-v2",
        generated_at=datetime(2026, 5, 2, 12, 0, tzinfo=UTC),
        world_bounds=TaxonomyCardScopeWorldBounds(min_x=0, min_y=0, max_x=1, max_y=1),
        nodes=[TaxonomyCardScopeLayoutNode(id=11, scope="inner", x=0.0, y=0.0)],
        edges=[],
    )


def _fingerprint_for_inner_nodes(node_ids: list[int]) -> str:
    return taxonomy_service_module._card_scope_layout_input_fingerprint(
        taxonomy_service_module._CardScopeGraphProjection(
            edges=[],
            scope_by_node_id=dict.fromkeys(node_ids, "inner"),
        )
    )


def _precompute_tree() -> list[TaxonomyNodeRecord]:
    return [
        TaxonomyNodeRecord(id=1, parent_id=None, name="Root", route_slug="root", depth=0),
        TaxonomyNodeRecord(id=2, parent_id=1, name="Science", route_slug="science", depth=1),
        TaxonomyNodeRecord(id=3, parent_id=1, name="Math", route_slug="math", depth=1),
        TaxonomyNodeRecord(id=4, parent_id=2, name="Heat", route_slug="heat", depth=2),
    ]


@pytest.mark.anyio
async def test_card_scope_precompute_targets_match_user_enterable_card_scopes() -> None:
    repo = _StubRepo(
        tree_nodes=_precompute_tree(),
        assignment_counts=[
            TaxonomyAssignmentCount(taxonomy_node_id=1, card_count=2),
            TaxonomyAssignmentCount(taxonomy_node_id=2, card_count=3),
            TaxonomyAssignmentCount(taxonomy_node_id=3, card_count=7),
            TaxonomyAssignmentCount(taxonomy_node_id=4, card_count=5),
        ],
    )
    service = TaxonomyService(repo=repo)

    targets = await service.list_card_scope_precompute_targets()

    assert [
        (
            target.route_path,
            target.scope_identity.scope_kind,
            target.scope_identity.taxonomy_node_id,
        )
        for target in targets
    ] == [
        ("math", TAXONOMY_NODE_SCOPE_KIND, 3),
        ("science/heat", TAXONOMY_NODE_SCOPE_KIND, 4),
        ("science/unclassified", VIRTUAL_UNCLASSIFIED_SCOPE_KIND, 2),
        ("unclassified", VIRTUAL_UNCLASSIFIED_SCOPE_KIND, 1),
    ]


@pytest.mark.anyio
async def test_card_scope_precompute_prepare_queues_missing_layout_without_building() -> None:
    scope_identity = TaxonomyScopeIdentity(
        scope_kind=TAXONOMY_NODE_SCOPE_KIND,
        taxonomy_node_id=2,
    )
    target = TaxonomyCardScopePrecomputeTarget(
        scope_identity=scope_identity,
        route_path="science",
        name="Science",
    )
    repo = _StubRepo(
        tree_nodes=_tree(),
        assigned_node_ids_by_scope={(TAXONOMY_NODE_SCOPE_KIND, 2): [11]},
    )
    service = TaxonomyService(
        repo=repo,
        knowledge_projection_port=_StubProjectionPort(),
        view_cache=_StubViewCache(layout=None),
    )

    result = await service.prepare_card_scope_layout_precompute_target(target=target)

    assert result.status == "queued"
    assert result.target == target
    assert repo.requested_layout_computes == [
        (scope_identity, _fingerprint_for_inner_nodes([11])),
    ]
    assert repo.stored_layout_writes == []
    assert repo.committed is True


@pytest.mark.anyio
async def test_card_scope_precompute_prepare_returns_ready_for_current_durable_layout() -> None:
    scope_identity = TaxonomyScopeIdentity(
        scope_kind=TAXONOMY_NODE_SCOPE_KIND,
        taxonomy_node_id=2,
    )
    target = TaxonomyCardScopePrecomputeTarget(
        scope_identity=scope_identity,
        route_path="science",
        name="Science",
    )
    repo = _StubRepo(
        tree_nodes=_tree(),
        assigned_node_ids_by_scope={(TAXONOMY_NODE_SCOPE_KIND, 2): [11]},
        stored_layout=_StoredLayout(
            input_fingerprint=_fingerprint_for_inner_nodes([11]),
            layout=_layout(),
        ),
    )
    service = TaxonomyService(
        repo=repo,
        knowledge_projection_port=_StubProjectionPort(),
        view_cache=_StubViewCache(layout=None),
    )

    result = await service.prepare_card_scope_layout_precompute_target(target=target)

    assert result.status == "ready"
    assert repo.requested_layout_computes == []


@pytest.mark.anyio
async def test_card_scope_precompute_prepare_refreshes_stale_layout() -> None:
    scope_identity = TaxonomyScopeIdentity(
        scope_kind=TAXONOMY_NODE_SCOPE_KIND,
        taxonomy_node_id=2,
    )
    target = TaxonomyCardScopePrecomputeTarget(
        scope_identity=scope_identity,
        route_path="science",
        name="Science",
    )
    repo = _StubRepo(
        tree_nodes=_tree(),
        assigned_node_ids_by_scope={(TAXONOMY_NODE_SCOPE_KIND, 2): [11, 12]},
        stored_layout=_StoredLayout(input_fingerprint="old-fingerprint", layout=_layout()),
    )
    service = TaxonomyService(
        repo=repo,
        knowledge_projection_port=_StubProjectionPort(),
        view_cache=_StubViewCache(layout=None),
    )

    result = await service.prepare_card_scope_layout_precompute_target(target=target)

    assert result.status == "refreshing"
    assert repo.requested_layout_computes == [
        (scope_identity, _fingerprint_for_inner_nodes([11, 12])),
    ]


@pytest.mark.anyio
async def test_card_scope_precompute_prepare_reports_failed_current_compute() -> None:
    scope_identity = TaxonomyScopeIdentity(
        scope_kind=TAXONOMY_NODE_SCOPE_KIND,
        taxonomy_node_id=2,
    )
    target = TaxonomyCardScopePrecomputeTarget(
        scope_identity=scope_identity,
        route_path="science",
        name="Science",
    )
    current_fingerprint = _fingerprint_for_inner_nodes([11])
    repo = _StubRepo(
        tree_nodes=_tree(),
        assigned_node_ids_by_scope={(TAXONOMY_NODE_SCOPE_KIND, 2): [11]},
        compute_request=_StoredComputeRequest(
            input_fingerprint=current_fingerprint,
            status="failed",
            last_error="layout compute failed",
        ),
    )
    service = TaxonomyService(
        repo=repo,
        knowledge_projection_port=_StubProjectionPort(),
        view_cache=_StubViewCache(layout=None),
    )

    result = await service.prepare_card_scope_layout_precompute_target(target=target)

    assert result.status == "failed"
    assert result.error_message == "layout compute failed"
    assert repo.requested_layout_computes == []


@pytest.mark.anyio
async def test_root_view_adds_virtual_unclassified_only_when_root_has_cards_and_children() -> None:
    repo = _StubRepo(
        tree_nodes=_tree(),
        assignment_counts=[
            TaxonomyAssignmentCount(taxonomy_node_id=1, card_count=2),
            TaxonomyAssignmentCount(taxonomy_node_id=2, card_count=5),
        ],
    )
    service = TaxonomyService(repo=repo)

    view = await service.get_root_view()

    assert [(child.name, child.scope_kind, child.node_kind) for child in view.children] == [
        ("Science", TAXONOMY_NODE_SCOPE_KIND, "card_scope"),
        ("Unclassified", VIRTUAL_UNCLASSIFIED_SCOPE_KIND, "card_scope"),
    ]
    assert view.children[1].taxonomy_node_id is None
    assert view.children[1].parent_taxonomy_node_id == 1


@pytest.mark.anyio
async def test_node_view_for_scope_with_only_cards_returns_card_scope_payload() -> None:
    repo = _StubRepo(
        tree_nodes=_tree(),
        assignment_counts=[TaxonomyAssignmentCount(taxonomy_node_id=2, card_count=5)],
        assigned_node_ids_by_scope={(TAXONOMY_NODE_SCOPE_KIND, 2): [11]},
    )
    service = TaxonomyService(
        repo=repo,
        knowledge_projection_port=_StubProjectionPort(),
        view_cache=_StubViewCache(
            layout=_layout(),
            input_fingerprint=_fingerprint_for_inner_nodes([11]),
        ),
    )

    view = await service.get_node_view(node_id=2)

    assert view.node_kind == "card_scope"
    assert view.current_scope.scope_kind == TAXONOMY_NODE_SCOPE_KIND
    assert view.current_scope.taxonomy_node_id == 2
    assert view.layout_version == "taxonomy-card-scope-layout-v2"


@pytest.mark.anyio
async def test_card_scope_without_cached_layout_raises_layout_not_ready() -> None:
    repo = _StubRepo(
        tree_nodes=_tree(),
        assignment_counts=[TaxonomyAssignmentCount(taxonomy_node_id=2, card_count=5)],
    )
    service = TaxonomyService(
        repo=repo,
        knowledge_projection_port=_StubProjectionPort(),
        view_cache=_StubViewCache(layout=None),
    )

    with pytest.raises(ApplicationError) as exc_info:
        await service.get_node_view(node_id=2)

    assert exc_info.value.code is ErrorCode.APPLICATION_TAXONOMY_LAYOUT_NOT_READY
    assert exc_info.value.safe_details == {
        "scope_kind": TAXONOMY_NODE_SCOPE_KIND,
        "taxonomy_node_id": 2,
    }


@pytest.mark.anyio
async def test_card_scope_serves_stored_stale_layout_and_requests_refresh() -> None:
    scope_identity = TaxonomyScopeIdentity(
        scope_kind=TAXONOMY_NODE_SCOPE_KIND,
        taxonomy_node_id=2,
    )
    repo = _StubRepo(
        tree_nodes=_tree(),
        assignment_counts=[TaxonomyAssignmentCount(taxonomy_node_id=2, card_count=5)],
        assigned_node_ids_by_scope={(TAXONOMY_NODE_SCOPE_KIND, 2): [11, 12]},
        stored_layout=_StoredLayout(input_fingerprint="old-fingerprint", layout=_layout()),
    )
    service = TaxonomyService(
        repo=repo,
        knowledge_projection_port=_StubProjectionPort(),
        view_cache=_StubViewCache(layout=None),
    )

    view = await service.get_node_view(node_id=2)

    assert view.node_kind == "card_scope"
    assert view.layout_status == "refreshing"
    assert view.node_count == 1
    assert len(repo.requested_layout_computes) == 1
    assert repo.requested_layout_computes[0][0] == scope_identity
    assert repo.requested_layout_computes[0][1] != "old-fingerprint"


@pytest.mark.anyio
async def test_card_scope_serves_cached_stale_layout_and_requests_refresh() -> None:
    scope_identity = TaxonomyScopeIdentity(
        scope_kind=TAXONOMY_NODE_SCOPE_KIND,
        taxonomy_node_id=2,
    )
    repo = _StubRepo(
        tree_nodes=_tree(),
        assignment_counts=[TaxonomyAssignmentCount(taxonomy_node_id=2, card_count=5)],
        assigned_node_ids_by_scope={(TAXONOMY_NODE_SCOPE_KIND, 2): [11, 12]},
    )
    service = TaxonomyService(
        repo=repo,
        knowledge_projection_port=_StubProjectionPort(),
        view_cache=_StubViewCache(
            layout=_layout(),
            input_fingerprint="old-fingerprint",
        ),
    )

    view = await service.get_node_view(node_id=2)

    assert view.node_kind == "card_scope"
    assert view.layout_status == "refreshing"
    assert view.node_count == 1
    assert len(repo.requested_layout_computes) == 1
    assert repo.requested_layout_computes[0][0] == scope_identity
    assert repo.requested_layout_computes[0][1] != "old-fingerprint"


@pytest.mark.anyio
async def test_build_and_cache_card_scope_layout_persists_durable_read_model() -> None:
    scope_identity = TaxonomyScopeIdentity(
        scope_kind=TAXONOMY_NODE_SCOPE_KIND,
        taxonomy_node_id=2,
    )
    repo = _StubRepo(
        tree_nodes=_tree(),
        assigned_node_ids_by_scope={(TAXONOMY_NODE_SCOPE_KIND, 2): [11]},
    )
    cache = _StubViewCache()
    service = TaxonomyService(
        repo=repo,
        knowledge_projection_port=_StubProjectionPort(),
        view_cache=cache,
    )

    layout = await service.build_and_cache_card_scope_layout(scope_identity=scope_identity)

    assert repo.stored_layout_writes == [(scope_identity, repo.stored_layout_writes[0][1], layout)]
    assert len(repo.stored_layout_writes[0][1]) == 64
    assert cache.layout == layout
    assert repo.committed is True


@pytest.mark.anyio
async def test_build_and_cache_card_scope_layout_offloads_sync_layout_build(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[Callable[..., object]] = []

    async def fake_to_thread(
        func: Callable[..., object],
        /,
        *args: object,
        **kwargs: object,
    ) -> object:
        calls.append(func)
        return func(*args, **kwargs)

    monkeypatch.setattr(taxonomy_service_module.asyncio, "to_thread", fake_to_thread)
    scope_identity = TaxonomyScopeIdentity(
        scope_kind=TAXONOMY_NODE_SCOPE_KIND,
        taxonomy_node_id=2,
    )
    repo = _StubRepo(
        tree_nodes=_tree(),
        assigned_node_ids_by_scope={(TAXONOMY_NODE_SCOPE_KIND, 2): [11]},
    )
    service = TaxonomyService(
        repo=repo,
        knowledge_projection_port=_StubProjectionPort(),
        view_cache=_StubViewCache(),
    )

    await service.build_and_cache_card_scope_layout(scope_identity=scope_identity)

    assert calls == [taxonomy_service_module._build_card_scope_layout_from_graph]


@pytest.mark.anyio
async def test_set_current_assignment_refreshes_previous_and_current_scope_identities() -> None:
    previous_scope = TaxonomyScopeIdentity(
        scope_kind=VIRTUAL_UNCLASSIFIED_SCOPE_KIND,
        taxonomy_node_id=1,
    )
    current_scope = TaxonomyScopeIdentity(
        scope_kind=TAXONOMY_NODE_SCOPE_KIND,
        taxonomy_node_id=2,
    )
    repo = _StubRepo(
        scope_identity_results=[{41: previous_scope}, {41: current_scope}],
        assigned_node_ids_by_scope={
            (VIRTUAL_UNCLASSIFIED_SCOPE_KIND, 1): [11],
            (TAXONOMY_NODE_SCOPE_KIND, 2): [41],
        },
        set_result=TaxonomyAssignmentRecord(
            id=7,
            node_id=41,
            taxonomy_node=TaxonomyNodeRecord(
                id=2,
                parent_id=1,
                name="Science",
                route_slug="science",
                depth=1,
            ),
            assigned_at=datetime(2026, 5, 2, 12, 0, tzinfo=UTC),
        ),
    )
    projection_port = _StubProjectionPort(adjacent_edge_ids=[101])
    service = TaxonomyService(repo=repo, knowledge_projection_port=projection_port)

    result = await service.set_current_assignment(node_id=41, taxonomy_node_id=2)

    assert result.node_id == 41
    assert repo.scope_identity_by_node_id_calls == [[41], [41]]
    assert repo.cleared_scope_identities == [current_scope, previous_scope]
    assert repo.added_scope_batches == [(current_scope, [101]), (previous_scope, [101])]
    assert projection_port.adjacent_requests == [[41], [11]]
    assert repo.committed is True
