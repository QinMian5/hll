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
    TaxonomyAssignmentRecord,
    TaxonomyLeafAssignment,
    TaxonomyLeafAssignmentCount,
    TaxonomyLeafLayout,
    TaxonomyLeafLayoutEdge,
    TaxonomyLeafLayoutNode,
    TaxonomyNodeRecord,
    TaxonomyTreeNode,
)
from modules.taxonomy.layout import (
    TAXONOMY_LEAF_LAYOUT_VERSION,
    build_leaf_layout,
    slice_leaf_layout,
)
from modules.taxonomy.route_path import join_taxonomy_route_path
from modules.taxonomy.schema import (
    TaxonomyLeafLayoutNodeResponse,
    TaxonomyLeafLayoutSliceResponse,
    TaxonomyLeafNodeDetailResponse,
    TaxonomyLeafNodeDetailsResponse,
    TaxonomyLeafNodeTitleResponse,
    TaxonomyLeafNodeTitlesResponse,
    TaxonomyLeafWorldBoundsResponse,
    TaxonomyNodeBranchViewResponse,
    TaxonomyNodeLeafViewResponse,
    TaxonomyNodeViewResponse,
    TaxonomyRootViewResponse,
    TaxonomyViewChildResponse,
    TaxonomyViewNodeResponse,
)

logger = logging.getLogger(__name__)


class TaxonomyRepoProtocol(Protocol):
    async def list_tree_nodes(self) -> list[TaxonomyNodeRecord]: ...

    async def get_node_by_id(self, *, node_id: int) -> TaxonomyNodeRecord | None: ...

    async def list_children(self, *, parent_id: int | None) -> list[TaxonomyNodeRecord]: ...

    async def get_assignment_for_node(self, *, node_id: int) -> TaxonomyAssignmentRecord | None: ...

    async def list_final_assignments(self) -> list[TaxonomyLeafAssignment]: ...

    async def list_leaf_assignment_counts(self) -> list[TaxonomyLeafAssignmentCount]: ...

    async def list_assigned_node_ids_for_leaf(self, *, leaf_id: int) -> list[int]: ...

    async def list_projected_edge_ids_for_leaf(self, *, leaf_id: int) -> list[int]: ...

    async def add_projected_edge_ids_for_leaf(
        self,
        *,
        leaf_id: int,
        edge_ids: list[int],
    ) -> None: ...

    async def clear_projected_edge_ids_for_leaf(self, *, leaf_id: int) -> None: ...

    async def list_leaf_ids_for_node_ids(self, *, node_ids: list[int]) -> dict[int, int]: ...

    async def set_current_assignment(
        self,
        *,
        node_id: int,
        taxonomy_node_id: int,
    ) -> TaxonomyAssignmentRecord: ...

    async def assign_node_to_root_unclassified(self, *, node_id: int) -> int: ...

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
    ) -> TaxonomyNodeBranchViewResponse | TaxonomyNodeLeafViewResponse | None: ...

    async def set_node_view(
        self,
        *,
        node_id: int,
        view: TaxonomyNodeBranchViewResponse | TaxonomyNodeLeafViewResponse,
    ) -> None: ...

    async def get_path_view(
        self,
        *,
        route_path: str,
    ) -> TaxonomyNodeBranchViewResponse | TaxonomyNodeLeafViewResponse | None: ...

    async def set_path_view(
        self,
        *,
        route_path: str,
        view: TaxonomyNodeBranchViewResponse | TaxonomyNodeLeafViewResponse,
    ) -> None: ...

    async def get_descendant_counts(self) -> dict[int, int] | None: ...

    async def set_descendant_counts(self, counts: dict[int, int]) -> None: ...

    async def acquire_descendant_counts_lock(self) -> bool: ...

    async def get_leaf_layout(self, *, leaf_id: int) -> TaxonomyLeafLayout | None: ...

    async def set_leaf_layout(self, *, leaf_id: int, layout: TaxonomyLeafLayout) -> None: ...

    async def acquire_leaf_layout_lock(self, *, leaf_id: int) -> bool: ...

    async def request_leaf_layout_compute(self, *, leaf_id: int) -> bool: ...


@dataclass(slots=True)
class _LeafGraphProjection:
    edges: list[ProjectionEdge]
    scope_by_node_id: dict[int, Literal["inner", "outer"]]


@dataclass(slots=True)
class _TaxonomyTreeContext:
    node_by_id: dict[int, TaxonomyNodeRecord]
    child_ids_by_parent: dict[int | None, list[int]]
    root: TaxonomyNodeRecord
    route_paths_by_id: dict[int, str]


def _view_node_from_record(
    record: TaxonomyNodeRecord,
    *,
    route_path: str,
) -> TaxonomyViewNodeResponse:
    return TaxonomyViewNodeResponse(
        id=record.id,
        parent_id=record.parent_id,
        name=record.name,
        route_slug=record.route_slug,
        route_path=route_path,
        depth=record.depth,
        is_leaf=record.is_leaf,
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

    async def get_root_view(self) -> TaxonomyRootViewResponse:
        cached_view = await self._get_cached_root_view()
        if cached_view is not None:
            return cached_view

        tree_context = await self._load_tree_context()
        descendant_counts = await self._load_descendant_card_counts(
            node_by_id=tree_context.node_by_id,
            child_ids_by_parent=tree_context.child_ids_by_parent,
        )
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
            descendant_counts=descendant_counts,
            route_paths_by_id=tree_context.route_paths_by_id,
        )
        view = TaxonomyRootViewResponse(breadcrumb=[], children=children)
        await self._set_cached_root_view(view)
        return view

    async def get_node_view(self, *, node_id: int) -> TaxonomyNodeViewResponse:
        cached_view = await self._get_cached_node_view(node_id=node_id)
        if cached_view is not None:
            return cached_view

        tree_context = await self._load_tree_context()
        view = await self._get_node_view_from_tree_context(
            node_id=node_id,
            tree_context=tree_context,
        )
        await self._set_cached_node_view(node_id=node_id, view=view)
        return view

    async def get_node_view_by_route_path(self, *, route_path: str) -> TaxonomyNodeViewResponse:
        cached_view = await self._get_cached_path_view(route_path=route_path)
        if cached_view is not None:
            return cached_view

        tree_context = await self._load_tree_context()
        node_id = _resolve_node_id_by_route_path(
            route_path=route_path,
            root=tree_context.root,
            child_ids_by_parent=tree_context.child_ids_by_parent,
            node_by_id=tree_context.node_by_id,
        )
        view = await self._get_node_view_from_tree_context(
            node_id=node_id,
            tree_context=tree_context,
        )
        await self._set_cached_path_view(route_path=route_path, view=view)
        return view

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
    ) -> TaxonomyNodeBranchViewResponse | TaxonomyNodeLeafViewResponse | None:
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
        view: TaxonomyNodeBranchViewResponse | TaxonomyNodeLeafViewResponse,
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
    ) -> TaxonomyNodeBranchViewResponse | TaxonomyNodeLeafViewResponse | None:
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
        view: TaxonomyNodeBranchViewResponse | TaxonomyNodeLeafViewResponse,
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

    async def _get_node_view_from_tree_context(
        self,
        *,
        node_id: int,
        tree_context: _TaxonomyTreeContext,
    ) -> TaxonomyNodeViewResponse:
        current_node = tree_context.node_by_id.get(node_id)
        if current_node is None:
            raise DomainError(
                code=ErrorCode.DOMAIN_TAXONOMY_RESOURCE_NOT_FOUND,
                message=f"Taxonomy node {node_id} was not found.",
                hint="Use an existing taxonomy node id and retry.",
            )

        breadcrumb = [
            _view_node_from_record(
                record,
                route_path=tree_context.route_paths_by_id[record.id],
            )
            for record in _build_breadcrumb(
                current_node_id=node_id,
                node_by_id=tree_context.node_by_id,
            )
        ]

        if not current_node.is_leaf:
            descendant_counts = await self._load_descendant_card_counts(
                node_by_id=tree_context.node_by_id,
                child_ids_by_parent=tree_context.child_ids_by_parent,
            )
            child_ids = sorted(
                tree_context.child_ids_by_parent.get(current_node.id, []),
                key=lambda child_node_id: (
                    tree_context.node_by_id[child_node_id].name,
                    tree_context.node_by_id[child_node_id].id,
                ),
            )
            children = _view_children_from_node_ids(
                child_ids=child_ids,
                node_by_id=tree_context.node_by_id,
                descendant_counts=descendant_counts,
                route_paths_by_id=tree_context.route_paths_by_id,
            )
            return TaxonomyNodeBranchViewResponse(
                node_kind="branch",
                current_node=_view_node_from_record(
                    current_node,
                    route_path=tree_context.route_paths_by_id[current_node.id],
                ),
                breadcrumb=breadcrumb,
                children=children,
            )

        leaf_layout = await self._load_ready_leaf_layout(current_node=current_node)
        return TaxonomyNodeLeafViewResponse(
            node_kind="leaf",
            current_node=_view_node_from_record(
                current_node,
                route_path=tree_context.route_paths_by_id[current_node.id],
            ),
            breadcrumb=breadcrumb,
            layout_version=TAXONOMY_LEAF_LAYOUT_VERSION,
            world_bounds=_world_bounds_response_from_layout(leaf_layout),
            node_count=leaf_layout.node_count,
            edge_count=leaf_layout.edge_count,
            generated_at=leaf_layout.generated_at,
        )

    async def get_leaf_layout_slice(
        self,
        *,
        node_id: int,
        min_x: float,
        min_y: float,
        max_x: float,
        max_y: float,
    ) -> TaxonomyLeafLayoutSliceResponse:
        tree_nodes = await self._repo.list_tree_nodes()
        node_by_id, _ = _index_tree(tree_nodes)
        if not node_by_id:
            raise DomainError(
                code=ErrorCode.DOMAIN_TAXONOMY_RESOURCE_NOT_FOUND,
                message="Taxonomy tree is not available.",
                hint="Import taxonomy data and retry.",
            )

        current_node = node_by_id.get(node_id)
        if current_node is None:
            raise DomainError(
                code=ErrorCode.DOMAIN_TAXONOMY_RESOURCE_NOT_FOUND,
                message=f"Taxonomy node {node_id} was not found.",
                hint="Use an existing taxonomy node id and retry.",
            )
        if not current_node.is_leaf:
            raise ApplicationError(
                code=ErrorCode.APPLICATION_TAXONOMY_INPUT_INVALID,
                message="Leaf layout request requires a leaf taxonomy node.",
                hint="Use a leaf taxonomy node id and retry.",
            )

        if min_x > max_x or min_y > max_y:
            raise ApplicationError(
                code=ErrorCode.APPLICATION_TAXONOMY_INPUT_INVALID,
                message="Leaf layout request bounds are invalid.",
                hint="Use min bounds less than or equal to max bounds and retry.",
            )

        leaf_layout = await self._load_ready_leaf_layout(current_node=current_node)
        layout_slice = slice_leaf_layout(
            leaf_layout,
            min_x=min_x,
            min_y=min_y,
            max_x=max_x,
            max_y=max_y,
        )
        return TaxonomyLeafLayoutSliceResponse(
            leaf_id=current_node.id,
            layout_version=layout_slice.layout_version,
            requested_bounds=TaxonomyLeafWorldBoundsResponse(
                min_x=layout_slice.requested_bounds.min_x,
                min_y=layout_slice.requested_bounds.min_y,
                max_x=layout_slice.requested_bounds.max_x,
                max_y=layout_slice.requested_bounds.max_y,
            ),
            nodes=[
                TaxonomyLeafLayoutNodeResponse(
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

    async def _validate_leaf_detail_node_ids(
        self,
        *,
        node_id: int,
        node_ids: list[int],
    ) -> _LeafGraphProjection:
        tree_nodes = await self._repo.list_tree_nodes()
        node_by_id, _ = _index_tree(tree_nodes)
        if not node_by_id:
            raise DomainError(
                code=ErrorCode.DOMAIN_TAXONOMY_RESOURCE_NOT_FOUND,
                message="Taxonomy tree is not available.",
                hint="Import taxonomy data and retry.",
            )

        current_node = node_by_id.get(node_id)
        if current_node is None:
            raise DomainError(
                code=ErrorCode.DOMAIN_TAXONOMY_RESOURCE_NOT_FOUND,
                message=f"Taxonomy node {node_id} was not found.",
                hint="Use an existing taxonomy node id and retry.",
            )

        if not current_node.is_leaf:
            raise ApplicationError(
                code=ErrorCode.APPLICATION_TAXONOMY_INPUT_INVALID,
                message="Leaf detail request requires a leaf taxonomy node.",
                hint="Use a leaf taxonomy node id and retry.",
            )

        if not node_ids:
            raise ApplicationError(
                code=ErrorCode.APPLICATION_TAXONOMY_INPUT_INVALID,
                message="Leaf detail request requires at least one node id.",
                hint="Send only unique node ids from the active leaf graph and retry.",
            )

        if len(node_ids) != len(set(node_ids)):
            raise ApplicationError(
                code=ErrorCode.APPLICATION_TAXONOMY_INPUT_INVALID,
                message="Leaf detail request contains duplicate node ids.",
                hint="Send only unique node ids from the active leaf graph and retry.",
            )

        leaf_graph = await self._build_leaf_graph_projection(current_node=current_node)
        invalid_node_ids = [
            requested_node_id
            for requested_node_id in node_ids
            if requested_node_id not in leaf_graph.scope_by_node_id
        ]
        if invalid_node_ids:
            raise ApplicationError(
                code=ErrorCode.APPLICATION_TAXONOMY_INPUT_INVALID,
                message="Leaf detail request references nodes outside the active leaf graph.",
                hint="Send only unique node ids from the active leaf graph and retry.",
            )

        if self._knowledge_projection_port is None:
            raise RuntimeError("Taxonomy leaf graph view requires knowledge projection dependency.")

        return leaf_graph

    async def get_leaf_node_details(
        self,
        *,
        node_id: int,
        node_ids: list[int],
    ) -> TaxonomyLeafNodeDetailsResponse:
        await self._validate_leaf_detail_node_ids(node_id=node_id, node_ids=node_ids)
        projection_port = self._knowledge_projection_port
        if projection_port is None:
            raise RuntimeError(
                "Taxonomy leaf detail view requires knowledge projection dependency."
            )

        requested_projection_nodes = await projection_port.list_projection_cards_for_node_ids(
            node_ids=node_ids
        )
        nodes_by_id = {node.node_id: node for node in requested_projection_nodes}
        if len(nodes_by_id) != len(node_ids):
            raise RuntimeError("Leaf detail request returned incomplete node details.")

        return TaxonomyLeafNodeDetailsResponse(
            nodes=[
                TaxonomyLeafNodeDetailResponse(
                    id=requested_node_id,
                    current_version=nodes_by_id[requested_node_id].current_version,
                    title=nodes_by_id[requested_node_id].title,
                    content=nodes_by_id[requested_node_id].content,
                )
                for requested_node_id in node_ids
            ]
        )

    async def get_leaf_node_titles(
        self,
        *,
        node_id: int,
        node_ids: list[int],
    ) -> TaxonomyLeafNodeTitlesResponse:
        await self._validate_leaf_detail_node_ids(node_id=node_id, node_ids=node_ids)
        projection_port = self._knowledge_projection_port
        if projection_port is None:
            raise RuntimeError("Taxonomy leaf title view requires knowledge projection dependency.")

        requested_projection_nodes = await projection_port.list_projection_card_titles_for_node_ids(
            node_ids=node_ids
        )
        nodes_by_id = {node.node_id: node for node in requested_projection_nodes}
        if len(nodes_by_id) != len(node_ids):
            raise RuntimeError("Leaf title request returned incomplete node titles.")

        return TaxonomyLeafNodeTitlesResponse(
            nodes=[
                TaxonomyLeafNodeTitleResponse(
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
            previous_assignment = await self._repo.get_assignment_for_node(node_id=node_id)
            previous_leaf_id = (
                None if previous_assignment is None else previous_assignment.taxonomy_node.id
            )
            assignment = await self._repo.set_current_assignment(
                node_id=node_id,
                taxonomy_node_id=taxonomy_node_id,
            )
            if self._knowledge_projection_port is not None:
                leaf_ids = {taxonomy_node_id}
                if previous_leaf_id is not None:
                    leaf_ids.add(previous_leaf_id)
                for leaf_id in sorted(leaf_ids):
                    await self._refresh_leaf_projection(leaf_id=leaf_id)
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

    async def assign_node_to_root_unclassified(self, *, node_id: int) -> int:
        try:
            leaf_id = await self._repo.assign_node_to_root_unclassified(node_id=node_id)
            if self._knowledge_projection_port is not None:
                await self._refresh_leaf_projection(leaf_id=leaf_id)
            await self._repo.commit()
            return leaf_id
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

        assignment_counts = await self._repo.list_leaf_assignment_counts()
        descendant_counts = dict.fromkeys(node_by_id, 0)
        for assignment_count in assignment_counts:
            descendant_counts[assignment_count.taxonomy_leaf_id] += assignment_count.card_count

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

    async def _build_leaf_graph_projection(
        self,
        *,
        current_node: TaxonomyNodeRecord,
    ) -> _LeafGraphProjection:
        if self._knowledge_projection_port is None:
            raise RuntimeError("Taxonomy leaf graph view requires knowledge projection dependency.")

        inner_node_ids = await self._repo.list_assigned_node_ids_for_leaf(leaf_id=current_node.id)
        projected_edge_ids = await self._repo.list_projected_edge_ids_for_leaf(
            leaf_id=current_node.id
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

        return _LeafGraphProjection(
            edges=edges,
            scope_by_node_id=scope_by_node_id,
        )

    async def build_and_cache_leaf_layout(self, *, leaf_id: int) -> TaxonomyLeafLayout:
        current_node = await self._repo.get_node_by_id(node_id=leaf_id)
        if current_node is None:
            raise DomainError(
                code=ErrorCode.DOMAIN_TAXONOMY_RESOURCE_NOT_FOUND,
                message=f"Taxonomy node {leaf_id} was not found.",
                hint="Use an existing taxonomy node id and retry.",
            )
        if not current_node.is_leaf:
            raise ApplicationError(
                code=ErrorCode.APPLICATION_TAXONOMY_INPUT_INVALID,
                message="Leaf layout compute requires a leaf taxonomy node.",
                hint="Use a leaf taxonomy node id and retry.",
            )

        layout = await self._build_leaf_layout(current_node=current_node)
        await self._set_cached_leaf_layout(leaf_id=current_node.id, layout=layout)
        return layout

    async def _load_ready_leaf_layout(
        self,
        *,
        current_node: TaxonomyNodeRecord,
    ) -> TaxonomyLeafLayout:
        cached_layout = await self._get_cached_leaf_layout(leaf_id=current_node.id)
        if cached_layout is not None:
            return cached_layout

        await self._request_leaf_layout_compute(leaf_id=current_node.id)
        raise _layout_not_ready_error(leaf_id=current_node.id)

    async def _build_leaf_layout(
        self,
        *,
        current_node: TaxonomyNodeRecord,
    ) -> TaxonomyLeafLayout:
        leaf_graph = await self._build_leaf_graph_projection(current_node=current_node)
        return build_leaf_layout(
            nodes=[
                TaxonomyLeafLayoutNode(
                    id=node_id,
                    scope=leaf_graph.scope_by_node_id[node_id],
                    x=0.0,
                    y=0.0,
                )
                for node_id in sorted(leaf_graph.scope_by_node_id)
            ],
            edges=[
                TaxonomyLeafLayoutEdge(
                    source_node_id=edge.node_a_id,
                    target_node_id=edge.node_b_id,
                    strength=edge.strength,
                )
                for edge in leaf_graph.edges
            ],
            generated_at=datetime.now(UTC),
        )

    async def _get_cached_leaf_layout(self, *, leaf_id: int) -> TaxonomyLeafLayout | None:
        if self._view_cache is None:
            return None
        try:
            return await self._view_cache.get_leaf_layout(leaf_id=leaf_id)
        except Exception as exc:
            _log_cache_failure(cache_name="taxonomy-leaf-layout", operation="get", exc=exc)
            return None

    async def _set_cached_leaf_layout(self, *, leaf_id: int, layout: TaxonomyLeafLayout) -> None:
        if self._view_cache is None:
            return
        try:
            await self._view_cache.set_leaf_layout(leaf_id=leaf_id, layout=layout)
        except Exception as exc:
            _log_cache_failure(cache_name="taxonomy-leaf-layout", operation="set", exc=exc)

    async def _acquire_leaf_layout_lock(self, *, leaf_id: int) -> None:
        if self._view_cache is None:
            return
        try:
            await self._view_cache.acquire_leaf_layout_lock(leaf_id=leaf_id)
        except Exception as exc:
            _log_cache_failure(cache_name="taxonomy-leaf-layout", operation="lock", exc=exc)

    async def _request_leaf_layout_compute(self, *, leaf_id: int) -> None:
        if self._view_cache is None:
            return
        try:
            await self._view_cache.request_leaf_layout_compute(leaf_id=leaf_id)
        except Exception as exc:
            _log_cache_failure(cache_name="taxonomy-leaf-layout", operation="request", exc=exc)

    async def _refresh_leaf_projection(self, *, leaf_id: int) -> None:
        if self._knowledge_projection_port is None:
            return
        inner_node_ids = await self._repo.list_assigned_node_ids_for_leaf(leaf_id=leaf_id)
        adjacent_edge_ids = (
            await self._knowledge_projection_port.list_adjacent_edge_ids_for_node_ids(
                node_ids=inner_node_ids
            )
        )
        await self._repo.clear_projected_edge_ids_for_leaf(leaf_id=leaf_id)
        await self._repo.add_projected_edge_ids_for_leaf(
            leaf_id=leaf_id,
            edge_ids=adjacent_edge_ids,
        )


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
    descendant_counts: dict[int, int],
    route_paths_by_id: dict[int, str],
) -> list[TaxonomyViewChildResponse]:
    return [
        TaxonomyViewChildResponse(
            id=node_by_id[node_id].id,
            parent_id=node_by_id[node_id].parent_id,
            name=node_by_id[node_id].name,
            route_slug=node_by_id[node_id].route_slug,
            route_path=route_paths_by_id[node_id],
            depth=node_by_id[node_id].depth,
            is_leaf=node_by_id[node_id].is_leaf,
            descendant_card_count=descendant_counts[node_id],
        )
        for node_id in child_ids
        if descendant_counts[node_id] > 0
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


def _log_cache_failure(*, cache_name: str, operation: str, exc: Exception) -> None:
    logger.warning(
        "Taxonomy cache failure.",
        extra={
            "cache_name": cache_name,
            "cache_operation": operation,
            "reason": str(exc),
        },
    )


def _layout_not_ready_error(*, leaf_id: int) -> ApplicationError:
    return ApplicationError(
        code=ErrorCode.APPLICATION_TAXONOMY_LAYOUT_NOT_READY,
        message="Taxonomy leaf layout is being prepared.",
        hint="Retry this request shortly.",
        safe_details={"leaf_id": leaf_id},
    )


def _world_bounds_response_from_layout(
    layout: TaxonomyLeafLayout,
) -> TaxonomyLeafWorldBoundsResponse:
    return TaxonomyLeafWorldBoundsResponse(
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
