"""
Abstract: Taxonomy service boundary for tree reads and final assignment persistence.
Out of scope: HTTP endpoint wiring and LLM classification orchestration.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal, Protocol

from core.errors import ApplicationError, DomainError, ErrorCode
from modules.knowledge_graph.dto import ProjectionCardNode, ProjectionCardTitle, ProjectionEdge
from modules.taxonomy.dto import (
    TaxonomyAssignmentCount,
    TaxonomyAssignmentRecord,
    TaxonomyCardScopeLayout,
    TaxonomyCardScopeLayoutEdge,
    TaxonomyCardScopeLayoutNode,
    TaxonomyNodeRecord,
    TaxonomyScopeAssignment,
    TaxonomyScopeIdentity,
    TaxonomyTreeNode,
)
from modules.taxonomy.layout import (
    TAXONOMY_CARD_SCOPE_LAYOUT_VERSION,
    build_card_scope_layout,
    slice_card_scope_layout,
)
from modules.taxonomy.repo import (
    TAXONOMY_NODE_SCOPE_KIND,
    UNCLASSIFIED_NODE_NAME,
    VIRTUAL_UNCLASSIFIED_SCOPE_KIND,
)
from modules.taxonomy.route_path import join_taxonomy_route_path
from modules.taxonomy.schema import (
    TaxonomyCardScopeLayoutNodeResponse,
    TaxonomyCardScopeLayoutSliceResponse,
    TaxonomyCardScopeNodeDetailResponse,
    TaxonomyCardScopeNodeDetailsResponse,
    TaxonomyCardScopeNodeTitleResponse,
    TaxonomyCardScopeNodeTitlesResponse,
    TaxonomyCardScopeWorldBoundsResponse,
    TaxonomyNodeBranchViewResponse,
    TaxonomyNodeCardScopeViewResponse,
    TaxonomyNodeViewResponse,
    TaxonomyRootViewResponse,
    TaxonomyViewChildResponse,
    TaxonomyViewScopeResponse,
)

logger = logging.getLogger(__name__)


class TaxonomyRepoProtocol(Protocol):
    async def list_tree_nodes(self) -> list[TaxonomyNodeRecord]: ...

    async def get_node_by_id(self, *, node_id: int) -> TaxonomyNodeRecord | None: ...

    async def list_children(self, *, parent_id: int | None) -> list[TaxonomyNodeRecord]: ...

    async def get_assignment_for_node(self, *, node_id: int) -> TaxonomyAssignmentRecord | None: ...

    async def list_current_assignments(self) -> list[TaxonomyScopeAssignment]: ...

    async def list_assignment_counts(self) -> list[TaxonomyAssignmentCount]: ...

    async def list_assigned_node_ids_for_scope(
        self,
        *,
        scope_identity: TaxonomyScopeIdentity,
    ) -> list[int]: ...

    async def list_projected_edge_ids_for_scope(
        self,
        *,
        scope_identity: TaxonomyScopeIdentity,
    ) -> list[int]: ...

    async def add_projected_edge_ids_for_scope(
        self,
        *,
        scope_identity: TaxonomyScopeIdentity,
        edge_ids: list[int],
    ) -> None: ...

    async def clear_projected_edge_ids_for_scope(
        self,
        *,
        scope_identity: TaxonomyScopeIdentity,
    ) -> None: ...

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

    async def set_current_assignment(
        self,
        *,
        node_id: int,
        taxonomy_node_id: int,
    ) -> TaxonomyAssignmentRecord: ...

    async def assign_node_to_root(self, *, node_id: int) -> int: ...

    async def commit(self) -> None: ...

    async def rollback(self) -> None: ...


class TaxonomyKnowledgeProjectionPort(Protocol):
    async def list_projection_cards_for_node_ids(
        self,
        *,
        node_ids: list[int],
    ) -> list[ProjectionCardNode]: ...

    async def list_projection_card_titles_for_node_ids(
        self,
        *,
        node_ids: list[int],
    ) -> list[ProjectionCardTitle]: ...

    async def list_projection_edges_touching_node_ids(
        self,
        *,
        node_ids: list[int],
    ) -> list[ProjectionEdge]: ...

    async def list_projection_edges_for_edge_ids(
        self,
        *,
        edge_ids: list[int],
    ) -> list[ProjectionEdge]: ...

    async def list_adjacent_edge_ids_for_node_ids(
        self,
        *,
        node_ids: list[int],
    ) -> list[int]: ...


class TaxonomyViewCachePort(Protocol):
    async def get_root_view(self) -> TaxonomyRootViewResponse | None: ...

    async def set_root_view(self, view: TaxonomyRootViewResponse) -> None: ...

    async def get_node_view(
        self,
        *,
        node_id: int,
    ) -> TaxonomyNodeBranchViewResponse | TaxonomyNodeCardScopeViewResponse | None: ...

    async def set_node_view(
        self,
        *,
        node_id: int,
        view: TaxonomyNodeBranchViewResponse | TaxonomyNodeCardScopeViewResponse,
    ) -> None: ...

    async def get_path_view(
        self,
        *,
        route_path: str,
    ) -> TaxonomyNodeBranchViewResponse | TaxonomyNodeCardScopeViewResponse | None: ...

    async def set_path_view(
        self,
        *,
        route_path: str,
        view: TaxonomyNodeBranchViewResponse | TaxonomyNodeCardScopeViewResponse,
    ) -> None: ...

    async def get_descendant_counts(self) -> dict[int, int] | None: ...

    async def set_descendant_counts(self, counts: dict[int, int]) -> None: ...

    async def acquire_descendant_counts_lock(self) -> bool: ...

    async def get_card_scope_layout(
        self,
        *,
        scope_identity: TaxonomyScopeIdentity,
    ) -> TaxonomyCardScopeLayout | None: ...

    async def set_card_scope_layout(
        self,
        *,
        scope_identity: TaxonomyScopeIdentity,
        layout: TaxonomyCardScopeLayout,
    ) -> None: ...

    async def acquire_card_scope_layout_lock(
        self,
        *,
        scope_identity: TaxonomyScopeIdentity,
    ) -> bool: ...

    async def request_card_scope_layout_compute(
        self,
        *,
        scope_identity: TaxonomyScopeIdentity,
    ) -> bool: ...


@dataclass(slots=True)
class _CardScopeGraphProjection:
    edges: list[ProjectionEdge]
    scope_by_node_id: dict[int, Literal["inner", "outer"]]


@dataclass(slots=True)
class _TaxonomyTreeContext:
    node_by_id: dict[int, TaxonomyNodeRecord]
    child_ids_by_parent: dict[int | None, list[int]]
    root: TaxonomyNodeRecord
    route_paths_by_id: dict[int, str]


@dataclass(slots=True, frozen=True)
class _ResolvedTaxonomyScope:
    identity: TaxonomyScopeIdentity
    current_scope: TaxonomyViewScopeResponse
    breadcrumb: list[TaxonomyViewScopeResponse]


def _view_scope_from_record(
    record: TaxonomyNodeRecord,
    *,
    route_path: str,
) -> TaxonomyViewScopeResponse:
    return TaxonomyViewScopeResponse(
        scope_kind=TAXONOMY_NODE_SCOPE_KIND,
        taxonomy_node_id=record.id,
        parent_taxonomy_node_id=record.parent_id,
        name=record.name,
        route_slug=record.route_slug,
        route_path=route_path,
        depth=record.depth,
    )


def _virtual_unclassified_scope_from_parent(
    parent: TaxonomyNodeRecord,
    *,
    parent_route_path: str,
) -> TaxonomyViewScopeResponse:
    return TaxonomyViewScopeResponse(
        scope_kind=VIRTUAL_UNCLASSIFIED_SCOPE_KIND,
        taxonomy_node_id=None,
        parent_taxonomy_node_id=parent.id,
        name=UNCLASSIFIED_NODE_NAME,
        route_slug="unclassified",
        route_path=join_taxonomy_route_path([parent_route_path, "unclassified"]),
        depth=parent.depth + 1,
    )


class TaxonomyService:
    def __init__(
        self,
        *,
        repo: TaxonomyRepoProtocol,
        knowledge_projection_port: TaxonomyKnowledgeProjectionPort | None = None,
        view_cache: TaxonomyViewCachePort | None = None,
    ) -> None:
        self._repo = repo
        self._knowledge_projection_port = knowledge_projection_port
        self._view_cache = view_cache

    async def list_tree(self) -> list[TaxonomyTreeNode]:
        records = await self._repo.list_tree_nodes()
        tree_nodes_by_id: dict[int, TaxonomyTreeNode] = {}
        roots: list[TaxonomyTreeNode] = []

        for record in records:
            tree_node = TaxonomyTreeNode(
                id=record.id,
                parent_id=record.parent_id,
                name=record.name,
                route_slug=record.route_slug,
                depth=record.depth,
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

    async def get_root_view(self) -> TaxonomyRootViewResponse:
        cached_view = await self._get_cached_root_view()
        if cached_view is not None:
            return cached_view

        tree_context = await self._load_tree_context()
        descendant_counts = await self._load_descendant_card_counts(
            node_by_id=tree_context.node_by_id,
            child_ids_by_parent=tree_context.child_ids_by_parent,
        )
        direct_counts = await self._load_direct_card_counts(node_by_id=tree_context.node_by_id)
        root_child_ids = sorted(
            tree_context.child_ids_by_parent.get(tree_context.root.id, []),
            key=lambda node_id: (
                tree_context.node_by_id[node_id].name,
                tree_context.node_by_id[node_id].id,
            ),
        )
        children = _view_children_from_node_ids(
            child_ids=root_child_ids,
            node_by_id=tree_context.node_by_id,
            child_ids_by_parent=tree_context.child_ids_by_parent,
            descendant_counts=descendant_counts,
            route_paths_by_id=tree_context.route_paths_by_id,
        )
        if direct_counts[tree_context.root.id] > 0 and children:
            children.append(
                _virtual_unclassified_child_response(
                    parent=tree_context.root,
                    parent_route_path=tree_context.route_paths_by_id[tree_context.root.id],
                    direct_card_count=direct_counts[tree_context.root.id],
                )
            )
        view = TaxonomyRootViewResponse(breadcrumb=[], children=children)
        await self._set_cached_root_view(view)
        return view

    async def get_node_view(self, *, node_id: int) -> TaxonomyNodeViewResponse:
        cached_view = await self._get_cached_node_view(node_id=node_id)
        if cached_view is not None:
            return cached_view

        tree_context = await self._load_tree_context()
        current_node = tree_context.node_by_id.get(node_id)
        if current_node is None:
            raise DomainError(
                code=ErrorCode.DOMAIN_TAXONOMY_RESOURCE_NOT_FOUND,
                message=f"Taxonomy node {node_id} was not found.",
                hint="Use an existing taxonomy node id and retry.",
            )
        view = await self._get_scope_view_from_tree_context(
            resolved_scope=_real_scope_from_node(
                node=current_node,
                tree_context=tree_context,
            ),
            tree_context=tree_context,
        )
        await self._set_cached_node_view(node_id=node_id, view=view)
        return view

    async def get_node_view_by_route_path(self, *, route_path: str) -> TaxonomyNodeViewResponse:
        cached_view = await self._get_cached_path_view(route_path=route_path)
        if cached_view is not None:
            return cached_view

        tree_context = await self._load_tree_context()
        resolved_scope = await self._resolve_scope_by_route_path(
            route_path=route_path,
            tree_context=tree_context,
        )
        view = await self._get_scope_view_from_tree_context(
            resolved_scope=resolved_scope,
            tree_context=tree_context,
        )
        await self._set_cached_path_view(route_path=route_path, view=view)
        return view

    async def _resolve_card_scope_by_route_path(
        self,
        *,
        route_path: str,
    ) -> _ResolvedTaxonomyScope:
        tree_context = await self._load_tree_context()
        resolved_scope = await self._resolve_scope_by_route_path(
            route_path=route_path,
            tree_context=tree_context,
        )
        await _resolve_card_scope_visibility(
            service=self,
            resolved_scope=resolved_scope,
            tree_context=tree_context,
        )
        return resolved_scope

    async def _resolve_scope_by_route_path(
        self,
        *,
        route_path: str,
        tree_context: _TaxonomyTreeContext,
    ) -> _ResolvedTaxonomyScope:
        if route_path.startswith("/") or route_path.endswith("/") or "//" in route_path:
            raise _route_path_not_found(route_path)
        if route_path == "":
            return _real_scope_from_node(node=tree_context.root, tree_context=tree_context)

        cursor = tree_context.root
        segments = route_path.split("/")
        for index, segment in enumerate(segments):
            if segment == "unclassified":
                if index != len(segments) - 1:
                    raise _route_path_not_found(route_path)
                resolved_scope = _ResolvedTaxonomyScope(
                    identity=TaxonomyScopeIdentity(
                        scope_kind=VIRTUAL_UNCLASSIFIED_SCOPE_KIND,
                        taxonomy_node_id=cursor.id,
                    ),
                    current_scope=_virtual_unclassified_scope_from_parent(
                        cursor,
                        parent_route_path=tree_context.route_paths_by_id[cursor.id],
                    ),
                    breadcrumb=[
                        *_real_scope_from_node(
                            node=cursor,
                            tree_context=tree_context,
                        ).breadcrumb,
                        _virtual_unclassified_scope_from_parent(
                            cursor,
                            parent_route_path=tree_context.route_paths_by_id[cursor.id],
                        ),
                    ],
                )
                await _resolve_card_scope_visibility(
                    service=self,
                    resolved_scope=resolved_scope,
                    tree_context=tree_context,
                )
                return resolved_scope

            matches = [
                child_id
                for child_id in tree_context.child_ids_by_parent.get(cursor.id, [])
                if tree_context.node_by_id[child_id].route_slug == segment
            ]
            if len(matches) != 1:
                raise _route_path_not_found(route_path)
            cursor = tree_context.node_by_id[matches[0]]

        return _real_scope_from_node(node=cursor, tree_context=tree_context)

    async def _get_cached_root_view(self) -> TaxonomyRootViewResponse | None:
        if self._view_cache is None:
            return None
        try:
            return await self._view_cache.get_root_view()
        except Exception as exc:
            _log_cache_failure(cache_name="taxonomy-root-view", operation="get", exc=exc)
            return None

    async def _set_cached_root_view(self, view: TaxonomyRootViewResponse) -> None:
        if self._view_cache is None:
            return
        try:
            await self._view_cache.set_root_view(view)
        except Exception as exc:
            _log_cache_failure(cache_name="taxonomy-root-view", operation="set", exc=exc)

    async def _get_cached_node_view(
        self,
        *,
        node_id: int,
    ) -> TaxonomyNodeBranchViewResponse | TaxonomyNodeCardScopeViewResponse | None:
        if self._view_cache is None:
            return None
        try:
            return await self._view_cache.get_node_view(node_id=node_id)
        except Exception as exc:
            _log_cache_failure(cache_name="taxonomy-node-view", operation="get", exc=exc)
            return None

    async def _set_cached_node_view(
        self,
        *,
        node_id: int,
        view: TaxonomyNodeBranchViewResponse | TaxonomyNodeCardScopeViewResponse,
    ) -> None:
        if self._view_cache is None:
            return
        try:
            await self._view_cache.set_node_view(node_id=node_id, view=view)
        except Exception as exc:
            _log_cache_failure(cache_name="taxonomy-node-view", operation="set", exc=exc)

    async def _get_cached_path_view(
        self,
        *,
        route_path: str,
    ) -> TaxonomyNodeBranchViewResponse | TaxonomyNodeCardScopeViewResponse | None:
        if self._view_cache is None:
            return None
        try:
            return await self._view_cache.get_path_view(route_path=route_path)
        except Exception as exc:
            _log_cache_failure(cache_name="taxonomy-path-view", operation="get", exc=exc)
            return None

    async def _set_cached_path_view(
        self,
        *,
        route_path: str,
        view: TaxonomyNodeBranchViewResponse | TaxonomyNodeCardScopeViewResponse,
    ) -> None:
        if self._view_cache is None:
            return
        try:
            await self._view_cache.set_path_view(route_path=route_path, view=view)
        except Exception as exc:
            _log_cache_failure(cache_name="taxonomy-path-view", operation="set", exc=exc)

    async def _load_tree_context(self) -> _TaxonomyTreeContext:
        tree_nodes = await self._repo.list_tree_nodes()
        node_by_id, child_ids_by_parent = _index_tree(tree_nodes)
        if not node_by_id:
            raise DomainError(
                code=ErrorCode.DOMAIN_TAXONOMY_RESOURCE_NOT_FOUND,
                message="Taxonomy tree is not available.",
                hint="Import taxonomy data and retry.",
            )

        root = _require_single_root(
            node_by_id=node_by_id,
            child_ids_by_parent=child_ids_by_parent,
        )
        route_paths_by_id = _build_route_paths_by_id(
            root=root,
            child_ids_by_parent=child_ids_by_parent,
            node_by_id=node_by_id,
        )
        return _TaxonomyTreeContext(
            node_by_id=node_by_id,
            child_ids_by_parent=child_ids_by_parent,
            root=root,
            route_paths_by_id=route_paths_by_id,
        )

    async def _get_scope_view_from_tree_context(
        self,
        *,
        resolved_scope: _ResolvedTaxonomyScope,
        tree_context: _TaxonomyTreeContext,
    ) -> TaxonomyNodeViewResponse:
        current_node = tree_context.node_by_id[resolved_scope.identity.taxonomy_node_id]
        descendant_counts = await self._load_descendant_card_counts(
            node_by_id=tree_context.node_by_id,
            child_ids_by_parent=tree_context.child_ids_by_parent,
        )
        direct_counts = await self._load_direct_card_counts(node_by_id=tree_context.node_by_id)
        visible_child_ids = _visible_child_ids(
            node_id=current_node.id,
            child_ids_by_parent=tree_context.child_ids_by_parent,
            descendant_counts=descendant_counts,
        )

        if resolved_scope.identity.scope_kind == TAXONOMY_NODE_SCOPE_KIND and visible_child_ids:
            children = _view_children_from_node_ids(
                child_ids=visible_child_ids,
                node_by_id=tree_context.node_by_id,
                child_ids_by_parent=tree_context.child_ids_by_parent,
                descendant_counts=descendant_counts,
                route_paths_by_id=tree_context.route_paths_by_id,
            )
            if direct_counts[current_node.id] > 0:
                children.append(
                    _virtual_unclassified_child_response(
                        parent=current_node,
                        parent_route_path=tree_context.route_paths_by_id[current_node.id],
                        direct_card_count=direct_counts[current_node.id],
                    )
                )
            return TaxonomyNodeBranchViewResponse(
                node_kind="branch",
                current_scope=resolved_scope.current_scope,
                breadcrumb=resolved_scope.breadcrumb,
                children=children,
            )

        layout = await self._load_ready_card_scope_layout(scope_identity=resolved_scope.identity)
        return TaxonomyNodeCardScopeViewResponse(
            node_kind="card_scope",
            current_scope=resolved_scope.current_scope,
            breadcrumb=resolved_scope.breadcrumb,
            layout_version=TAXONOMY_CARD_SCOPE_LAYOUT_VERSION,
            world_bounds=_world_bounds_response_from_layout(layout),
            node_count=layout.node_count,
            edge_count=layout.edge_count,
            generated_at=layout.generated_at,
        )

    async def get_card_scope_layout_slice(
        self,
        *,
        route_path: str,
        min_x: float,
        min_y: float,
        max_x: float,
        max_y: float,
    ) -> TaxonomyCardScopeLayoutSliceResponse:
        if min_x > max_x or min_y > max_y:
            raise ApplicationError(
                code=ErrorCode.APPLICATION_TAXONOMY_INPUT_INVALID,
                message="Card-scope layout request bounds are invalid.",
                hint="Use min bounds less than or equal to max bounds and retry.",
            )

        resolved_scope = await self._resolve_card_scope_by_route_path(route_path=route_path)
        layout = await self._load_ready_card_scope_layout(scope_identity=resolved_scope.identity)
        layout_slice = slice_card_scope_layout(
            layout,
            min_x=min_x,
            min_y=min_y,
            max_x=max_x,
            max_y=max_y,
        )
        return TaxonomyCardScopeLayoutSliceResponse(
            scope_kind=resolved_scope.current_scope.scope_kind,
            taxonomy_node_id=resolved_scope.current_scope.taxonomy_node_id,
            parent_taxonomy_node_id=resolved_scope.current_scope.parent_taxonomy_node_id,
            route_path=resolved_scope.current_scope.route_path,
            layout_version=layout_slice.layout_version,
            requested_bounds=TaxonomyCardScopeWorldBoundsResponse(
                min_x=layout_slice.requested_bounds.min_x,
                min_y=layout_slice.requested_bounds.min_y,
                max_x=layout_slice.requested_bounds.max_x,
                max_y=layout_slice.requested_bounds.max_y,
            ),
            nodes=[
                TaxonomyCardScopeLayoutNodeResponse(
                    id=node.id,
                    scope=node.scope,
                    x=node.x,
                    y=node.y,
                )
                for node in layout_slice.nodes
            ],
            edges=[
                (edge.source_node_id, edge.target_node_id, edge.strength)
                for edge in layout_slice.edges
            ],
        )

    async def _validate_card_scope_detail_node_ids(
        self,
        *,
        route_path: str,
        node_ids: list[int],
    ) -> _CardScopeGraphProjection:
        if not node_ids:
            raise ApplicationError(
                code=ErrorCode.APPLICATION_TAXONOMY_INPUT_INVALID,
                message="Card-scope detail request requires at least one node id.",
                hint="Send only unique node ids from the active card-scope graph and retry.",
            )

        if len(node_ids) != len(set(node_ids)):
            raise ApplicationError(
                code=ErrorCode.APPLICATION_TAXONOMY_INPUT_INVALID,
                message="Card-scope detail request contains duplicate node ids.",
                hint="Send only unique node ids from the active card-scope graph and retry.",
            )

        resolved_scope = await self._resolve_card_scope_by_route_path(route_path=route_path)
        graph = await self._build_card_scope_graph_projection(
            scope_identity=resolved_scope.identity
        )
        invalid_node_ids = [
            requested_node_id
            for requested_node_id in node_ids
            if requested_node_id not in graph.scope_by_node_id
        ]
        if invalid_node_ids:
            raise ApplicationError(
                code=ErrorCode.APPLICATION_TAXONOMY_INPUT_INVALID,
                message="Card-scope detail request references nodes outside the active graph.",
                hint="Send only unique node ids from the active card-scope graph and retry.",
            )

        if self._knowledge_projection_port is None:
            raise RuntimeError(
                "Taxonomy card-scope graph view requires knowledge projection dependency."
            )

        return graph

    async def get_card_scope_node_details(
        self,
        *,
        route_path: str,
        node_ids: list[int],
    ) -> TaxonomyCardScopeNodeDetailsResponse:
        await self._validate_card_scope_detail_node_ids(route_path=route_path, node_ids=node_ids)
        projection_port = self._knowledge_projection_port
        if projection_port is None:
            raise RuntimeError(
                "Taxonomy card-scope detail view requires knowledge projection dependency."
            )

        requested_projection_nodes = await projection_port.list_projection_cards_for_node_ids(
            node_ids=node_ids
        )
        nodes_by_id = {node.node_id: node for node in requested_projection_nodes}
        if len(nodes_by_id) != len(node_ids):
            raise RuntimeError("Card-scope detail request returned incomplete node details.")

        return TaxonomyCardScopeNodeDetailsResponse(
            nodes=[
                TaxonomyCardScopeNodeDetailResponse(
                    id=requested_node_id,
                    current_version=nodes_by_id[requested_node_id].current_version,
                    title=nodes_by_id[requested_node_id].title,
                    content=nodes_by_id[requested_node_id].content,
                )
                for requested_node_id in node_ids
            ]
        )

    async def get_card_scope_node_titles(
        self,
        *,
        route_path: str,
        node_ids: list[int],
    ) -> TaxonomyCardScopeNodeTitlesResponse:
        await self._validate_card_scope_detail_node_ids(route_path=route_path, node_ids=node_ids)
        projection_port = self._knowledge_projection_port
        if projection_port is None:
            raise RuntimeError(
                "Taxonomy card-scope title view requires knowledge projection dependency."
            )

        requested_projection_nodes = await projection_port.list_projection_card_titles_for_node_ids(
            node_ids=node_ids
        )
        nodes_by_id = {node.node_id: node for node in requested_projection_nodes}
        if len(nodes_by_id) != len(node_ids):
            raise RuntimeError("Card-scope title request returned incomplete node titles.")

        return TaxonomyCardScopeNodeTitlesResponse(
            nodes=[
                TaxonomyCardScopeNodeTitleResponse(
                    id=requested_node_id,
                    title=nodes_by_id[requested_node_id].title,
                )
                for requested_node_id in node_ids
            ]
        )

    async def set_current_assignment(
        self,
        *,
        node_id: int,
        taxonomy_node_id: int,
    ) -> TaxonomyAssignmentRecord:
        try:
            previous_scope_identities = await self._repo.list_scope_identities_for_node_ids(
                node_ids=[node_id]
            )
            assignment = await self._repo.set_current_assignment(
                node_id=node_id,
                taxonomy_node_id=taxonomy_node_id,
            )
            if self._knowledge_projection_port is not None:
                current_scope_identities = await self._repo.list_scope_identities_for_node_ids(
                    node_ids=[node_id]
                )
                await self._refresh_card_scope_projections(
                    scope_identities=[
                        *previous_scope_identities.values(),
                        *current_scope_identities.values(),
                    ]
                )
            await self._repo.commit()
            return assignment
        except Exception:
            await self._repo.rollback()
            raise

    async def set_final_assignment(
        self,
        *,
        node_id: int,
        taxonomy_node_id: int,
    ) -> TaxonomyAssignmentRecord:
        return await self.set_current_assignment(
            node_id=node_id,
            taxonomy_node_id=taxonomy_node_id,
        )

    async def assign_node_to_root(self, *, node_id: int) -> int:
        try:
            previous_scope_identities = await self._repo.list_scope_identities_for_node_ids(
                node_ids=[node_id]
            )
            root_id = await self._repo.assign_node_to_root(node_id=node_id)
            if self._knowledge_projection_port is not None:
                current_scope_identities = await self._repo.list_scope_identities_for_node_ids(
                    node_ids=[node_id]
                )
                await self._refresh_card_scope_projections(
                    scope_identities=[
                        *previous_scope_identities.values(),
                        *current_scope_identities.values(),
                    ]
                )
            await self._repo.commit()
            return root_id
        except Exception:
            await self._repo.rollback()
            raise

    async def _load_descendant_card_counts(
        self,
        *,
        node_by_id: dict[int, TaxonomyNodeRecord],
        child_ids_by_parent: dict[int | None, list[int]],
    ) -> dict[int, int]:
        if self._view_cache is not None:
            cached_counts = await self._get_cached_descendant_counts()
            if cached_counts is not None:
                return {node_id: cached_counts.get(node_id, 0) for node_id in node_by_id}
            await self._acquire_descendant_counts_lock()

        descendant_counts = await self._load_direct_card_counts(node_by_id=node_by_id)

        for node in sorted(
            node_by_id.values(),
            key=lambda item: (item.depth, item.id),
            reverse=True,
        ):
            if node.parent_id is None:
                continue
            descendant_counts[node.parent_id] += descendant_counts[node.id]

        if self._view_cache is not None:
            await self._set_cached_descendant_counts(descendant_counts)

        return descendant_counts

    async def _load_direct_card_counts(
        self,
        *,
        node_by_id: dict[int, TaxonomyNodeRecord],
    ) -> dict[int, int]:
        assignment_counts = await self._repo.list_assignment_counts()
        direct_counts = dict.fromkeys(node_by_id, 0)
        for assignment_count in assignment_counts:
            if assignment_count.taxonomy_node_id in direct_counts:
                direct_counts[assignment_count.taxonomy_node_id] += assignment_count.card_count
        return direct_counts

    async def _get_cached_descendant_counts(self) -> dict[int, int] | None:
        if self._view_cache is None:
            return None
        try:
            return await self._view_cache.get_descendant_counts()
        except Exception as exc:
            _log_cache_failure(cache_name="taxonomy-descendant-counts", operation="get", exc=exc)
            return None

    async def _set_cached_descendant_counts(self, counts: dict[int, int]) -> None:
        if self._view_cache is None:
            return
        try:
            await self._view_cache.set_descendant_counts(counts)
        except Exception as exc:
            _log_cache_failure(cache_name="taxonomy-descendant-counts", operation="set", exc=exc)

    async def _acquire_descendant_counts_lock(self) -> None:
        if self._view_cache is None:
            return
        try:
            await self._view_cache.acquire_descendant_counts_lock()
        except Exception as exc:
            _log_cache_failure(cache_name="taxonomy-descendant-counts", operation="lock", exc=exc)

    async def _build_card_scope_graph_projection(
        self,
        *,
        scope_identity: TaxonomyScopeIdentity,
    ) -> _CardScopeGraphProjection:
        if self._knowledge_projection_port is None:
            raise RuntimeError(
                "Taxonomy card-scope graph view requires knowledge projection dependency."
            )

        inner_node_ids = await self._repo.list_assigned_node_ids_for_scope(
            scope_identity=scope_identity
        )
        projected_edge_ids = await self._repo.list_projected_edge_ids_for_scope(
            scope_identity=scope_identity
        )
        edges = await self._knowledge_projection_port.list_projection_edges_for_edge_ids(
            edge_ids=projected_edge_ids
        )
        all_node_ids = set(inner_node_ids)
        for edge in edges:
            all_node_ids.add(edge.node_a_id)
            all_node_ids.add(edge.node_b_id)
        inner_node_id_set = set(inner_node_ids)
        scope_by_node_id: dict[int, Literal["inner", "outer"]] = {}
        for related_node_id in sorted(all_node_ids):
            scope_by_node_id[related_node_id] = (
                "inner" if related_node_id in inner_node_id_set else "outer"
            )

        return _CardScopeGraphProjection(
            edges=edges,
            scope_by_node_id=scope_by_node_id,
        )

    async def build_and_cache_card_scope_layout(
        self,
        *,
        scope_identity: TaxonomyScopeIdentity,
    ) -> TaxonomyCardScopeLayout:
        current_node = await self._repo.get_node_by_id(node_id=scope_identity.taxonomy_node_id)
        if current_node is None:
            raise DomainError(
                code=ErrorCode.DOMAIN_TAXONOMY_RESOURCE_NOT_FOUND,
                message=f"Taxonomy node {scope_identity.taxonomy_node_id} was not found.",
                hint="Use an existing taxonomy node id and retry.",
            )

        layout = await self._build_card_scope_layout(scope_identity=scope_identity)
        await self._set_cached_card_scope_layout(scope_identity=scope_identity, layout=layout)
        return layout

    async def _load_ready_card_scope_layout(
        self,
        *,
        scope_identity: TaxonomyScopeIdentity,
    ) -> TaxonomyCardScopeLayout:
        cached_layout = await self._get_cached_card_scope_layout(scope_identity=scope_identity)
        if cached_layout is not None:
            return cached_layout

        await self._request_card_scope_layout_compute(scope_identity=scope_identity)
        raise _layout_not_ready_error(scope_identity=scope_identity)

    async def _build_card_scope_layout(
        self,
        *,
        scope_identity: TaxonomyScopeIdentity,
    ) -> TaxonomyCardScopeLayout:
        graph = await self._build_card_scope_graph_projection(scope_identity=scope_identity)
        return build_card_scope_layout(
            nodes=[
                TaxonomyCardScopeLayoutNode(
                    id=node_id,
                    scope=graph.scope_by_node_id[node_id],
                    x=0.0,
                    y=0.0,
                )
                for node_id in sorted(graph.scope_by_node_id)
            ],
            edges=[
                TaxonomyCardScopeLayoutEdge(
                    source_node_id=edge.node_a_id,
                    target_node_id=edge.node_b_id,
                    strength=edge.strength,
                )
                for edge in graph.edges
            ],
            generated_at=datetime.now(UTC),
        )

    async def _get_cached_card_scope_layout(
        self,
        *,
        scope_identity: TaxonomyScopeIdentity,
    ) -> TaxonomyCardScopeLayout | None:
        if self._view_cache is None:
            return None
        try:
            return await self._view_cache.get_card_scope_layout(scope_identity=scope_identity)
        except Exception as exc:
            _log_cache_failure(cache_name="taxonomy-card-scope-layout", operation="get", exc=exc)
            return None

    async def _set_cached_card_scope_layout(
        self,
        *,
        scope_identity: TaxonomyScopeIdentity,
        layout: TaxonomyCardScopeLayout,
    ) -> None:
        if self._view_cache is None:
            return
        try:
            await self._view_cache.set_card_scope_layout(
                scope_identity=scope_identity,
                layout=layout,
            )
        except Exception as exc:
            _log_cache_failure(cache_name="taxonomy-card-scope-layout", operation="set", exc=exc)

    async def _acquire_card_scope_layout_lock(
        self,
        *,
        scope_identity: TaxonomyScopeIdentity,
    ) -> None:
        if self._view_cache is None:
            return
        try:
            await self._view_cache.acquire_card_scope_layout_lock(scope_identity=scope_identity)
        except Exception as exc:
            _log_cache_failure(cache_name="taxonomy-card-scope-layout", operation="lock", exc=exc)

    async def _request_card_scope_layout_compute(
        self,
        *,
        scope_identity: TaxonomyScopeIdentity,
    ) -> None:
        if self._view_cache is None:
            return
        try:
            await self._view_cache.request_card_scope_layout_compute(scope_identity=scope_identity)
        except Exception as exc:
            _log_cache_failure(
                cache_name="taxonomy-card-scope-layout",
                operation="request",
                exc=exc,
            )

    async def _refresh_card_scope_projection(
        self,
        *,
        scope_identity: TaxonomyScopeIdentity,
    ) -> None:
        if self._knowledge_projection_port is None:
            return
        inner_node_ids = await self._repo.list_assigned_node_ids_for_scope(
            scope_identity=scope_identity
        )
        adjacent_edge_ids = (
            await self._knowledge_projection_port.list_adjacent_edge_ids_for_node_ids(
                node_ids=inner_node_ids
            )
        )
        await self._repo.clear_projected_edge_ids_for_scope(scope_identity=scope_identity)
        await self._repo.add_projected_edge_ids_for_scope(
            scope_identity=scope_identity,
            edge_ids=adjacent_edge_ids,
        )

    async def _refresh_card_scope_projections(
        self,
        *,
        scope_identities: list[TaxonomyScopeIdentity],
    ) -> None:
        deduped = {
            (scope_identity.scope_kind, scope_identity.taxonomy_node_id): scope_identity
            for scope_identity in scope_identities
        }
        for key in sorted(deduped):
            await self._refresh_card_scope_projection(scope_identity=deduped[key])


def _index_tree(
    tree_nodes: list[TaxonomyNodeRecord],
) -> tuple[dict[int, TaxonomyNodeRecord], dict[int | None, list[int]]]:
    node_by_id = {node.id: node for node in tree_nodes}
    child_ids_by_parent: dict[int | None, list[int]] = defaultdict(list)
    for node in tree_nodes:
        child_ids_by_parent[node.parent_id].append(node.id)
    return (node_by_id, child_ids_by_parent)


def _view_children_from_node_ids(
    *,
    child_ids: list[int],
    node_by_id: dict[int, TaxonomyNodeRecord],
    child_ids_by_parent: dict[int | None, list[int]],
    descendant_counts: dict[int, int],
    route_paths_by_id: dict[int, str],
) -> list[TaxonomyViewChildResponse]:
    return [
        _real_child_response(
            node=node_by_id[node_id],
            route_path=route_paths_by_id[node_id],
            node_kind=(
                "branch"
                if _visible_child_ids(
                    node_id=node_id,
                    child_ids_by_parent=child_ids_by_parent,
                    descendant_counts=descendant_counts,
                )
                else "card_scope"
            ),
            descendant_card_count=descendant_counts[node_id],
        )
        for node_id in child_ids
        if descendant_counts[node_id] > 0
    ]


def _real_child_response(
    *,
    node: TaxonomyNodeRecord,
    route_path: str,
    node_kind: Literal["branch", "card_scope"],
    descendant_card_count: int,
) -> TaxonomyViewChildResponse:
    return TaxonomyViewChildResponse(
        scope_kind=TAXONOMY_NODE_SCOPE_KIND,
        taxonomy_node_id=node.id,
        parent_taxonomy_node_id=node.parent_id,
        name=node.name,
        route_slug=node.route_slug,
        route_path=route_path,
        depth=node.depth,
        node_kind=node_kind,
        descendant_card_count=descendant_card_count,
    )


def _virtual_unclassified_child_response(
    *,
    parent: TaxonomyNodeRecord,
    parent_route_path: str,
    direct_card_count: int,
) -> TaxonomyViewChildResponse:
    return TaxonomyViewChildResponse(
        scope_kind=VIRTUAL_UNCLASSIFIED_SCOPE_KIND,
        taxonomy_node_id=None,
        parent_taxonomy_node_id=parent.id,
        name=UNCLASSIFIED_NODE_NAME,
        route_slug="unclassified",
        route_path=join_taxonomy_route_path([parent_route_path, "unclassified"]),
        depth=parent.depth + 1,
        node_kind="card_scope",
        descendant_card_count=direct_card_count,
    )


def _visible_child_ids(
    *,
    node_id: int,
    child_ids_by_parent: dict[int | None, list[int]],
    descendant_counts: dict[int, int],
) -> list[int]:
    return [
        child_id
        for child_id in sorted(child_ids_by_parent.get(node_id, []), key=lambda item: item)
        if descendant_counts[child_id] > 0
    ]


def _build_route_paths_by_id(
    *,
    root: TaxonomyNodeRecord,
    child_ids_by_parent: dict[int | None, list[int]],
    node_by_id: dict[int, TaxonomyNodeRecord],
) -> dict[int, str]:
    route_paths_by_id = {root.id: ""}
    stack = list(child_ids_by_parent.get(root.id, []))
    while stack:
        node_id = stack.pop()
        node = node_by_id[node_id]
        parent_id = node.parent_id
        assert parent_id is not None
        parent_route_path = route_paths_by_id[parent_id]
        route_paths_by_id[node.id] = join_taxonomy_route_path([parent_route_path, node.route_slug])
        stack.extend(child_ids_by_parent.get(node.id, []))
    return route_paths_by_id


def _resolve_node_id_by_route_path(
    *,
    route_path: str,
    root: TaxonomyNodeRecord,
    child_ids_by_parent: dict[int | None, list[int]],
    node_by_id: dict[int, TaxonomyNodeRecord],
) -> int:
    if (
        not route_path
        or route_path.startswith("/")
        or route_path.endswith("/")
        or "//" in route_path
    ):
        raise DomainError(
            code=ErrorCode.DOMAIN_TAXONOMY_RESOURCE_NOT_FOUND,
            message=f"Taxonomy route path {route_path!r} was not found.",
            hint="Use an existing taxonomy route path and retry.",
        )

    cursor_id = root.id
    for segment in route_path.split("/"):
        matches = [
            child_id
            for child_id in child_ids_by_parent.get(cursor_id, [])
            if node_by_id[child_id].route_slug == segment
        ]
        if len(matches) != 1:
            raise DomainError(
                code=ErrorCode.DOMAIN_TAXONOMY_RESOURCE_NOT_FOUND,
                message=f"Taxonomy route path {route_path!r} was not found.",
                hint="Use an existing taxonomy route path and retry.",
            )
        cursor_id = matches[0]

    return cursor_id


def _real_scope_from_node(
    *,
    node: TaxonomyNodeRecord,
    tree_context: _TaxonomyTreeContext,
) -> _ResolvedTaxonomyScope:
    return _ResolvedTaxonomyScope(
        identity=TaxonomyScopeIdentity(
            scope_kind=TAXONOMY_NODE_SCOPE_KIND,
            taxonomy_node_id=node.id,
        ),
        current_scope=_view_scope_from_record(
            node,
            route_path=tree_context.route_paths_by_id[node.id],
        ),
        breadcrumb=[
            _view_scope_from_record(
                record,
                route_path=tree_context.route_paths_by_id[record.id],
            )
            for record in _build_breadcrumb(
                current_node_id=node.id,
                node_by_id=tree_context.node_by_id,
            )
        ],
    )


async def _resolve_card_scope_visibility(
    *,
    service: TaxonomyService,
    resolved_scope: _ResolvedTaxonomyScope,
    tree_context: _TaxonomyTreeContext,
) -> None:
    current_node_id = resolved_scope.identity.taxonomy_node_id
    descendant_counts = await service._load_descendant_card_counts(
        node_by_id=tree_context.node_by_id,
        child_ids_by_parent=tree_context.child_ids_by_parent,
    )
    direct_counts = await service._load_direct_card_counts(node_by_id=tree_context.node_by_id)
    visible_child_ids = _visible_child_ids(
        node_id=current_node_id,
        child_ids_by_parent=tree_context.child_ids_by_parent,
        descendant_counts=descendant_counts,
    )
    if resolved_scope.identity.scope_kind == VIRTUAL_UNCLASSIFIED_SCOPE_KIND:
        if direct_counts[current_node_id] <= 0 or not visible_child_ids:
            raise DomainError(
                code=ErrorCode.DOMAIN_TAXONOMY_RESOURCE_NOT_FOUND,
                message=(
                    f"Taxonomy route path {resolved_scope.current_scope.route_path!r} "
                    "was not found."
                ),
                hint="Use an existing taxonomy route path and retry.",
            )
        return
    if visible_child_ids:
        raise ApplicationError(
            code=ErrorCode.APPLICATION_TAXONOMY_INPUT_INVALID,
            message="Card-scope request requires a card-scope route path.",
            hint="Use a route path returned with node_kind card_scope and retry.",
        )


def _route_path_not_found(route_path: str) -> DomainError:
    return DomainError(
        code=ErrorCode.DOMAIN_TAXONOMY_RESOURCE_NOT_FOUND,
        message=f"Taxonomy route path {route_path!r} was not found.",
        hint="Use an existing taxonomy route path and retry.",
    )


def _log_cache_failure(*, cache_name: str, operation: str, exc: Exception) -> None:
    logger.warning(
        "Taxonomy cache failure.",
        extra={
            "cache_name": cache_name,
            "cache_operation": operation,
            "reason": str(exc),
        },
    )


def _layout_not_ready_error(*, scope_identity: TaxonomyScopeIdentity) -> ApplicationError:
    return ApplicationError(
        code=ErrorCode.APPLICATION_TAXONOMY_LAYOUT_NOT_READY,
        message="Taxonomy card-scope layout is being prepared.",
        hint="Retry this request shortly.",
        safe_details=scope_identity.model_dump(mode="json"),
    )


def _world_bounds_response_from_layout(
    layout: TaxonomyCardScopeLayout,
) -> TaxonomyCardScopeWorldBoundsResponse:
    return TaxonomyCardScopeWorldBoundsResponse(
        min_x=layout.world_bounds.min_x,
        min_y=layout.world_bounds.min_y,
        max_x=layout.world_bounds.max_x,
        max_y=layout.world_bounds.max_y,
    )


def _require_single_root(
    *,
    node_by_id: dict[int, TaxonomyNodeRecord],
    child_ids_by_parent: dict[int | None, list[int]],
) -> TaxonomyNodeRecord:
    root_ids = child_ids_by_parent.get(None, [])
    if len(root_ids) != 1:
        raise DomainError(
            code=ErrorCode.DOMAIN_TAXONOMY_RESOURCE_NOT_FOUND,
            message="Taxonomy root is not available.",
            hint="Ensure exactly one Root taxonomy node exists and retry.",
        )
    return node_by_id[root_ids[0]]


def _build_breadcrumb(
    *,
    current_node_id: int,
    node_by_id: dict[int, TaxonomyNodeRecord],
) -> list[TaxonomyNodeRecord]:
    chain: list[TaxonomyNodeRecord] = []
    cursor = node_by_id[current_node_id]
    while True:
        chain.append(cursor)
        if cursor.parent_id is None:
            break
        cursor = node_by_id[cursor.parent_id]
    chain.reverse()
    return chain
