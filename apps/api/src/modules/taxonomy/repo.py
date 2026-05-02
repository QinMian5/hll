"""
Abstract: Async SQLAlchemy repository primitives for taxonomy bootstrap, tree reads,
and final assignments.
Out of scope: YAML parsing and HTTP transport wiring.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import delete, func, literal, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from modules.knowledge_graph.model import Node
from modules.taxonomy.dto import (
    TaxonomyAssignmentCount,
    TaxonomyAssignmentRecord,
    TaxonomyNodeRecord,
    TaxonomyScopeAssignment,
    TaxonomyScopeIdentity,
)
from modules.taxonomy.model import (
    NodeTaxonomyAssignment,
    TaxonomyNode,
    TaxonomyScopeProjectionEdge,
)
from modules.taxonomy.route_path import slugify_taxonomy_route_segment

ROOT_NODE_NAME = "Root"
UNCLASSIFIED_NODE_NAME = "Unclassified"
TAXONOMY_PROJECTION_EDGE_INSERT_BATCH_SIZE = 10_000
TAXONOMY_NODE_SCOPE_KIND = "taxonomy_node"
VIRTUAL_UNCLASSIFIED_SCOPE_KIND = "virtual_unclassified"


def _taxonomy_node_record_from_model(node: TaxonomyNode) -> TaxonomyNodeRecord:
    return TaxonomyNodeRecord(
        id=node.id,
        parent_id=node.parent_id,
        name=node.name,
        route_slug=node.route_slug,
        depth=node.depth,
    )


def _assignment_record_from_row(
    assignment: NodeTaxonomyAssignment,
    taxonomy_node: TaxonomyNode,
) -> TaxonomyAssignmentRecord:
    return TaxonomyAssignmentRecord(
        id=assignment.id,
        node_id=assignment.node_id,
        taxonomy_node=_taxonomy_node_record_from_model(taxonomy_node),
        assigned_at=assignment.assigned_at,
    )


class TaxonomyRepo:
    def __init__(self, *, session: AsyncSession) -> None:
        self._session = session

    async def has_any_taxonomy_nodes(self) -> bool:
        result = await self._session.execute(select(TaxonomyNode.id).limit(1))
        return result.scalar_one_or_none() is not None

    async def count_nodes(self) -> int:
        count = await self._session.scalar(select(func.count()).select_from(Node))
        return int(count or 0)

    async def count_taxonomy_assignments(self) -> int:
        count = await self._session.scalar(select(func.count()).select_from(NodeTaxonomyAssignment))
        return int(count or 0)

    async def count_nodes_missing_taxonomy_assignment(self) -> int:
        count = await self._session.scalar(
            select(func.count())
            .select_from(Node)
            .outerjoin(NodeTaxonomyAssignment, NodeTaxonomyAssignment.node_id == Node.id)
            .where(NodeTaxonomyAssignment.node_id.is_(None))
        )
        return int(count or 0)

    async def assign_unassigned_nodes_to_taxonomy_node(self, *, taxonomy_node_id: int) -> None:
        missing_nodes = (
            select(Node.id, literal(taxonomy_node_id))
            .outerjoin(NodeTaxonomyAssignment, NodeTaxonomyAssignment.node_id == Node.id)
            .where(NodeTaxonomyAssignment.node_id.is_(None))
        )
        await self._session.execute(
            insert(NodeTaxonomyAssignment)
            .from_select(["node_id", "taxonomy_node_id"], missing_nodes)
            .on_conflict_do_nothing(index_elements=["node_id"])
        )
        await self._session.flush()

    async def get_root_node(self) -> TaxonomyNodeRecord | None:
        node = await self._session.scalar(
            select(TaxonomyNode).where(TaxonomyNode.parent_id.is_(None)).limit(1)
        )
        if node is None:
            return None
        return _taxonomy_node_record_from_model(node)

    async def get_child_by_name(
        self,
        *,
        parent_id: int,
        name: str,
    ) -> TaxonomyNodeRecord | None:
        node = await self._session.scalar(
            select(TaxonomyNode)
            .where(TaxonomyNode.parent_id == parent_id)
            .where(TaxonomyNode.name == name)
            .limit(1)
        )
        if node is None:
            return None
        return _taxonomy_node_record_from_model(node)

    async def create_taxonomy_node(
        self,
        *,
        parent_id: int | None,
        name: str,
        depth: int,
    ) -> int:
        taxonomy_node = TaxonomyNode(
            parent_id=parent_id,
            name=name,
            route_slug=slugify_taxonomy_route_segment(name),
            depth=depth,
        )
        self._session.add(taxonomy_node)
        await self._session.flush()
        return taxonomy_node.id

    async def ensure_root(self) -> TaxonomyNodeRecord:
        root = await self.get_root_node()
        if root is None:
            root_id = await self.create_taxonomy_node(
                parent_id=None,
                name=ROOT_NODE_NAME,
                depth=0,
            )
            root = await self.get_node_by_id(node_id=root_id)
            if root is None:
                raise RuntimeError("Root taxonomy node was not readable after creation.")

        return root

    async def create_regular_child(
        self,
        *,
        parent_id: int,
        name: str,
    ) -> TaxonomyNodeRecord:
        parent = await self.get_node_by_id(node_id=parent_id)
        if parent is None:
            raise ValueError(f"Taxonomy parent node {parent_id} does not exist.")
        if name == UNCLASSIFIED_NODE_NAME:
            raise ValueError("Unclassified is a virtual scope and cannot be persisted.")

        child_id = await self.create_taxonomy_node(
            parent_id=parent.id,
            name=name,
            depth=parent.depth + 1,
        )
        child = await self.get_node_by_id(node_id=child_id)
        if child is None:
            raise RuntimeError("Created taxonomy child node was not readable.")
        return child

    async def list_tree_nodes(self) -> list[TaxonomyNodeRecord]:
        result = await self._session.scalars(
            select(TaxonomyNode).order_by(
                TaxonomyNode.depth.asc(),
                TaxonomyNode.parent_id.asc().nullsfirst(),
                TaxonomyNode.name.asc(),
                TaxonomyNode.id.asc(),
            )
        )
        return [_taxonomy_node_record_from_model(node) for node in result.all()]

    async def get_node_by_id(self, *, node_id: int) -> TaxonomyNodeRecord | None:
        node = await self._session.scalar(
            select(TaxonomyNode).where(TaxonomyNode.id == node_id).limit(1)
        )
        if node is None:
            return None
        return _taxonomy_node_record_from_model(node)

    async def list_children(self, *, parent_id: int | None) -> list[TaxonomyNodeRecord]:
        statement = select(TaxonomyNode)
        if parent_id is None:
            statement = statement.where(TaxonomyNode.parent_id.is_(None))
        else:
            statement = statement.where(TaxonomyNode.parent_id == parent_id)

        result = await self._session.scalars(
            statement.order_by(TaxonomyNode.name.asc(), TaxonomyNode.id.asc())
        )
        return [_taxonomy_node_record_from_model(node) for node in result.all()]

    async def get_assignment_for_node(self, *, node_id: int) -> TaxonomyAssignmentRecord | None:
        result = await self._session.execute(
            select(NodeTaxonomyAssignment, TaxonomyNode)
            .join(TaxonomyNode, TaxonomyNode.id == NodeTaxonomyAssignment.taxonomy_node_id)
            .where(NodeTaxonomyAssignment.node_id == node_id)
            .limit(1)
        )
        row = result.one_or_none()
        if row is None:
            return None

        assignment, taxonomy_node = row
        return _assignment_record_from_row(assignment, taxonomy_node)

    async def list_current_assignments(self) -> list[TaxonomyScopeAssignment]:
        rows = (
            await self._session.execute(
                select(
                    NodeTaxonomyAssignment.node_id,
                    NodeTaxonomyAssignment.taxonomy_node_id,
                ).order_by(NodeTaxonomyAssignment.node_id.asc())
            )
        ).all()
        return [
            TaxonomyScopeAssignment(
                node_id=row.node_id,
                taxonomy_node_id=row.taxonomy_node_id,
            )
            for row in rows
        ]

    async def list_assignment_counts(self) -> list[TaxonomyAssignmentCount]:
        rows = (
            await self._session.execute(
                select(
                    NodeTaxonomyAssignment.taxonomy_node_id,
                    func.count(NodeTaxonomyAssignment.node_id).label("card_count"),
                )
                .group_by(NodeTaxonomyAssignment.taxonomy_node_id)
                .order_by(NodeTaxonomyAssignment.taxonomy_node_id.asc())
            )
        ).all()
        return [
            TaxonomyAssignmentCount(
                taxonomy_node_id=row.taxonomy_node_id,
                card_count=row.card_count,
            )
            for row in rows
        ]

    async def list_assigned_node_ids_for_taxonomy_node(self, *, taxonomy_node_id: int) -> list[int]:
        rows = (
            await self._session.execute(
                select(NodeTaxonomyAssignment.node_id)
                .where(NodeTaxonomyAssignment.taxonomy_node_id == taxonomy_node_id)
                .order_by(NodeTaxonomyAssignment.node_id.asc())
            )
        ).all()
        return [row.node_id for row in rows]

    async def list_assigned_node_ids_for_scope(
        self,
        *,
        scope_identity: TaxonomyScopeIdentity,
    ) -> list[int]:
        return await self.list_assigned_node_ids_for_taxonomy_node(
            taxonomy_node_id=scope_identity.taxonomy_node_id
        )

    async def list_projected_edge_ids_for_scope(
        self,
        *,
        scope_identity: TaxonomyScopeIdentity,
    ) -> list[int]:
        rows = (
            await self._session.execute(
                select(TaxonomyScopeProjectionEdge.edge_id)
                .where(TaxonomyScopeProjectionEdge.scope_kind == scope_identity.scope_kind)
                .where(
                    TaxonomyScopeProjectionEdge.taxonomy_node_id == scope_identity.taxonomy_node_id
                )
                .order_by(TaxonomyScopeProjectionEdge.edge_id.asc())
            )
        ).all()
        return [row.edge_id for row in rows]

    async def add_projected_edge_ids_for_scope(
        self,
        *,
        scope_identity: TaxonomyScopeIdentity,
        edge_ids: list[int],
    ) -> None:
        deduped_edge_ids = sorted(set(edge_ids))
        for start in range(0, len(deduped_edge_ids), TAXONOMY_PROJECTION_EDGE_INSERT_BATCH_SIZE):
            batch = deduped_edge_ids[start : start + TAXONOMY_PROJECTION_EDGE_INSERT_BATCH_SIZE]
            statement = (
                insert(TaxonomyScopeProjectionEdge)
                .values(
                    [
                        {
                            "scope_kind": scope_identity.scope_kind,
                            "taxonomy_node_id": scope_identity.taxonomy_node_id,
                            "edge_id": edge_id,
                        }
                        for edge_id in batch
                    ]
                )
                .on_conflict_do_nothing(
                    index_elements=["scope_kind", "taxonomy_node_id", "edge_id"]
                )
            )
            await self._session.execute(statement)
        await self._session.flush()

    async def list_taxonomy_node_ids_for_node_ids(self, *, node_ids: list[int]) -> dict[int, int]:
        if not node_ids:
            return {}

        rows = (
            await self._session.execute(
                select(
                    NodeTaxonomyAssignment.node_id,
                    NodeTaxonomyAssignment.taxonomy_node_id,
                )
                .where(NodeTaxonomyAssignment.node_id.in_(node_ids))
                .order_by(NodeTaxonomyAssignment.node_id.asc())
            )
        ).all()
        return {row.node_id: row.taxonomy_node_id for row in rows}

    async def list_scope_identities_for_node_ids(
        self,
        *,
        node_ids: list[int],
    ) -> dict[int, TaxonomyScopeIdentity]:
        taxonomy_node_ids_by_node_id = await self.list_taxonomy_node_ids_for_node_ids(
            node_ids=node_ids
        )
        if not taxonomy_node_ids_by_node_id:
            return {}

        tree_nodes = await self.list_tree_nodes()
        node_by_id = {node.id: node for node in tree_nodes}
        child_ids_by_parent: dict[int | None, list[int]] = {}
        for node in tree_nodes:
            child_ids_by_parent.setdefault(node.parent_id, []).append(node.id)

        direct_counts = dict.fromkeys(node_by_id, 0)
        for count in await self.list_assignment_counts():
            if count.taxonomy_node_id in direct_counts:
                direct_counts[count.taxonomy_node_id] = count.card_count

        descendant_counts = dict(direct_counts)
        for node in sorted(
            node_by_id.values(),
            key=lambda item: (item.depth, item.id),
            reverse=True,
        ):
            if node.parent_id is not None:
                descendant_counts[node.parent_id] += descendant_counts[node.id]

        result: dict[int, TaxonomyScopeIdentity] = {}
        for node_id, taxonomy_node_id in taxonomy_node_ids_by_node_id.items():
            visible_child_ids = [
                child_id
                for child_id in child_ids_by_parent.get(taxonomy_node_id, [])
                if descendant_counts[child_id] > 0
            ]
            result[node_id] = TaxonomyScopeIdentity(
                scope_kind=(
                    VIRTUAL_UNCLASSIFIED_SCOPE_KIND
                    if visible_child_ids
                    else TAXONOMY_NODE_SCOPE_KIND
                ),
                taxonomy_node_id=taxonomy_node_id,
            )
        return result

    async def clear_all_projected_edge_ids(self) -> None:
        await self._session.execute(delete(TaxonomyScopeProjectionEdge))
        await self._session.flush()

    async def clear_projected_edge_ids_for_scope(
        self,
        *,
        scope_identity: TaxonomyScopeIdentity,
    ) -> None:
        await self._session.execute(
            delete(TaxonomyScopeProjectionEdge)
            .where(TaxonomyScopeProjectionEdge.scope_kind == scope_identity.scope_kind)
            .where(TaxonomyScopeProjectionEdge.taxonomy_node_id == scope_identity.taxonomy_node_id)
        )
        await self._session.flush()

    async def set_current_assignment(
        self,
        *,
        node_id: int,
        taxonomy_node_id: int,
    ) -> TaxonomyAssignmentRecord:
        assignment = await self._session.scalar(
            select(NodeTaxonomyAssignment).where(NodeTaxonomyAssignment.node_id == node_id).limit(1)
        )
        if assignment is None:
            assignment = NodeTaxonomyAssignment(
                node_id=node_id,
                taxonomy_node_id=taxonomy_node_id,
            )
            self._session.add(assignment)
        else:
            assignment.taxonomy_node_id = taxonomy_node_id
            assignment.assigned_at = datetime.now(UTC)

        await self._session.flush()
        stored_assignment = await self.get_assignment_for_node(node_id=node_id)
        if stored_assignment is None:
            raise RuntimeError("Current taxonomy assignment was not readable after persistence.")
        return stored_assignment

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
        root = await self.ensure_root()
        await self.set_current_assignment(
            node_id=node_id,
            taxonomy_node_id=root.id,
        )
        return root.id

    async def commit(self) -> None:
        await self._session.commit()

    async def rollback(self) -> None:
        await self._session.rollback()
