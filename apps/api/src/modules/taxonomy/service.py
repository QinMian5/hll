"""
Abstract: Taxonomy service boundary for tree reads and final assignment persistence.
Out of scope: HTTP endpoint wiring and LLM classification orchestration.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Literal, Protocol

from core.errors import ApplicationError, DomainError, ErrorCode
from modules.knowledge_graph.dto import ProjectionCardNode, ProjectionEdge
from modules.taxonomy.dto import (
    TaxonomyAssignmentRecord,
    TaxonomyLeafAssignment,
    TaxonomyNodeRecord,
    TaxonomyTreeNode,
)
from modules.taxonomy.schema import (
    TaxonomyLeafGraphNodeResponse,
    TaxonomyLeafNodeDetailResponse,
    TaxonomyLeafNodeDetailsResponse,
    TaxonomyNodeBranchViewResponse,
    TaxonomyNodeLeafViewResponse,
    TaxonomyNodeViewResponse,
    TaxonomyRootViewResponse,
    TaxonomyViewChildResponse,
    TaxonomyViewNodeResponse,
)


class TaxonomyRepoProtocol(Protocol):
    async def list_tree_nodes(self) -> list[TaxonomyNodeRecord]: ...

    async def get_node_by_id(self, *, node_id: int) -> TaxonomyNodeRecord | None: ...

    async def list_children(self, *, parent_id: int | None) -> list[TaxonomyNodeRecord]: ...

    async def get_assignment_for_node(self, *, node_id: int) -> TaxonomyAssignmentRecord | None: ...

    async def list_final_assignments(self) -> list[TaxonomyLeafAssignment]: ...

    async def list_assigned_node_ids_for_leaf(self, *, leaf_id: int) -> list[int]: ...

    async def list_projected_edge_ids_for_leaf(self, *, leaf_id: int) -> list[int]: ...

    async def add_projected_edge_ids_for_leaf(
        self,
        *,
        leaf_id: int,
        edge_ids: list[int],
    ) -> None: ...

    async def list_leaf_ids_for_node_ids(self, *, node_ids: list[int]) -> dict[int, int]: ...

    async def set_final_assignment(
        self,
        *,
        node_id: int,
        taxonomy_node_id: int,
    ) -> TaxonomyAssignmentRecord: ...

    async def commit(self) -> None: ...

    async def rollback(self) -> None: ...


class TaxonomyKnowledgeProjectionPort(Protocol):
    async def list_projection_cards_for_node_ids(
        self,
        *,
        node_ids: list[int],
    ) -> list[ProjectionCardNode]: ...

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


@dataclass(slots=True)
class _LeafGraphProjection:
    edges: list[ProjectionEdge]
    scope_by_node_id: dict[int, Literal["inner", "outer"]]


def _view_node_from_record(record: TaxonomyNodeRecord) -> TaxonomyViewNodeResponse:
    return TaxonomyViewNodeResponse(
        id=record.id,
        parent_id=record.parent_id,
        name=record.name,
        depth=record.depth,
        is_leaf=record.is_leaf,
    )


class TaxonomyService:
    def __init__(
        self,
        *,
        repo: TaxonomyRepoProtocol,
        knowledge_projection_port: TaxonomyKnowledgeProjectionPort | None = None,
    ) -> None:
        self._repo = repo
        self._knowledge_projection_port = knowledge_projection_port

    async def list_tree(self) -> list[TaxonomyTreeNode]:
        records = await self._repo.list_tree_nodes()
        tree_nodes_by_id: dict[int, TaxonomyTreeNode] = {}
        roots: list[TaxonomyTreeNode] = []

        for record in records:
            tree_node = TaxonomyTreeNode(
                id=record.id,
                parent_id=record.parent_id,
                name=record.name,
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
        tree_nodes = await self._repo.list_tree_nodes()
        node_by_id, child_ids_by_parent = _index_tree(tree_nodes)
        if not node_by_id:
            raise DomainError(
                code=ErrorCode.DOMAIN_TAXONOMY_RESOURCE_NOT_FOUND,
                message="Taxonomy tree is not available.",
                hint="Import taxonomy data and retry.",
            )

        descendant_counts = await self._load_descendant_card_counts(
            node_by_id=node_by_id,
            child_ids_by_parent=child_ids_by_parent,
        )
        root_ids = sorted(
            child_ids_by_parent.get(None, []),
            key=lambda node_id: (node_by_id[node_id].name, node_by_id[node_id].id),
        )
        children = [
            TaxonomyViewChildResponse(
                id=node_by_id[node_id].id,
                parent_id=node_by_id[node_id].parent_id,
                name=node_by_id[node_id].name,
                depth=node_by_id[node_id].depth,
                is_leaf=node_by_id[node_id].is_leaf,
                descendant_card_count=descendant_counts[node_id],
            )
            for node_id in root_ids
            if descendant_counts[node_id] > 0
        ]
        return TaxonomyRootViewResponse(breadcrumb=[], children=children)

    async def get_node_view(self, *, node_id: int) -> TaxonomyNodeViewResponse:
        tree_nodes = await self._repo.list_tree_nodes()
        node_by_id, child_ids_by_parent = _index_tree(tree_nodes)
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

        breadcrumb = [
            _view_node_from_record(record)
            for record in _build_breadcrumb(
                current_node_id=node_id,
                node_by_id=node_by_id,
            )
        ]

        if not current_node.is_leaf:
            descendant_counts = await self._load_descendant_card_counts(
                node_by_id=node_by_id,
                child_ids_by_parent=child_ids_by_parent,
            )
            child_ids = sorted(
                child_ids_by_parent.get(current_node.id, []),
                key=lambda child_node_id: (
                    node_by_id[child_node_id].name,
                    node_by_id[child_node_id].id,
                ),
            )
            children = [
                TaxonomyViewChildResponse(
                    id=node_by_id[child_node_id].id,
                    parent_id=node_by_id[child_node_id].parent_id,
                    name=node_by_id[child_node_id].name,
                    depth=node_by_id[child_node_id].depth,
                    is_leaf=node_by_id[child_node_id].is_leaf,
                    descendant_card_count=descendant_counts[child_node_id],
                )
                for child_node_id in child_ids
                if descendant_counts[child_node_id] > 0
            ]
            return TaxonomyNodeBranchViewResponse(
                node_kind="branch",
                current_node=_view_node_from_record(current_node),
                breadcrumb=breadcrumb,
                children=children,
            )

        if self._knowledge_projection_port is None:
            raise RuntimeError("Taxonomy leaf graph view requires knowledge projection dependency.")

        leaf_graph = await self._build_leaf_graph_projection(current_node=current_node)
        nodes = sorted(
            (
                TaxonomyLeafGraphNodeResponse(
                    id=node_id,
                    scope=scope,
                )
                for node_id, scope in leaf_graph.scope_by_node_id.items()
            ),
            key=lambda node: node.id,
        )

        edge_items = sorted(
            (
                (
                    edge.node_a_id,
                    edge.node_b_id,
                    edge.strength,
                )
                for edge in leaf_graph.edges
            ),
            key=lambda edge: (edge[0], edge[1]),
        )

        return TaxonomyNodeLeafViewResponse(
            node_kind="leaf",
            current_node=_view_node_from_record(current_node),
            breadcrumb=breadcrumb,
            nodes=nodes,
            edges=edge_items,
        )

    async def get_leaf_node_details(
        self,
        *,
        node_id: int,
        node_ids: list[int],
    ) -> TaxonomyLeafNodeDetailsResponse:
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

        requested_projection_nodes = (
            await self._knowledge_projection_port.list_projection_cards_for_node_ids(
                node_ids=node_ids
            )
        )
        nodes_by_id = {node.node_id: node for node in requested_projection_nodes}
        if len(nodes_by_id) != len(node_ids):
            raise RuntimeError("Leaf detail request returned incomplete node details.")

        return TaxonomyLeafNodeDetailsResponse(
            nodes=[
                TaxonomyLeafNodeDetailResponse(
                    id=requested_node_id,
                    title=nodes_by_id[requested_node_id].title,
                    content=nodes_by_id[requested_node_id].content,
                )
                for requested_node_id in node_ids
            ]
        )

    async def set_final_assignment(
        self,
        *,
        node_id: int,
        taxonomy_node_id: int,
    ) -> TaxonomyAssignmentRecord:
        try:
            assignment = await self._repo.set_final_assignment(
                node_id=node_id,
                taxonomy_node_id=taxonomy_node_id,
            )
            if self._knowledge_projection_port is not None:
                adjacent_edge_ids = (
                    await self._knowledge_projection_port.list_adjacent_edge_ids_for_node_ids(
                        node_ids=[node_id]
                    )
                )
                await self._repo.add_projected_edge_ids_for_leaf(
                    leaf_id=taxonomy_node_id,
                    edge_ids=adjacent_edge_ids,
                )
            await self._repo.commit()
            return assignment
        except Exception:
            await self._repo.rollback()
            raise

    async def _load_descendant_card_counts(
        self,
        *,
        node_by_id: dict[int, TaxonomyNodeRecord],
        child_ids_by_parent: dict[int | None, list[int]],
    ) -> dict[int, int]:
        assignments = await self._repo.list_final_assignments()
        descendant_counts = dict.fromkeys(node_by_id, 0)
        for assignment in assignments:
            descendant_counts[assignment.taxonomy_leaf_id] += 1

        for node in sorted(
            node_by_id.values(),
            key=lambda item: (item.depth, item.id),
            reverse=True,
        ):
            if node.parent_id is None:
                continue
            descendant_counts[node.parent_id] += descendant_counts[node.id]

        return descendant_counts

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

        return _LeafGraphProjection(
            edges=edges,
            scope_by_node_id={
                related_node_id: "inner" if related_node_id in inner_node_id_set else "outer"
                for related_node_id in sorted(all_node_ids)
            },
        )


def _index_tree(
    tree_nodes: list[TaxonomyNodeRecord],
) -> tuple[dict[int, TaxonomyNodeRecord], dict[int | None, list[int]]]:
    node_by_id = {node.id: node for node in tree_nodes}
    child_ids_by_parent: dict[int | None, list[int]] = defaultdict(list)
    for node in tree_nodes:
        child_ids_by_parent[node.parent_id].append(node.id)
    return (node_by_id, child_ids_by_parent)


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
