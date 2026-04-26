"""
Abstract: In-session taxonomy traversal and assignment operations used by Cursor classification.
Out of scope: Click CLI command parsing and runtime dependency assembly.
"""

from __future__ import annotations

from modules.taxonomy_classification.dto import (
    SessionAssignLeafResponse,
    SessionAssignmentResponse,
    SessionChildrenResponse,
)
from modules.taxonomy_classification.ports import TaxonomyClassificationSessionTaxonomyPort


class TaxonomyClassificationSessionTool:
    def __init__(
        self,
        *,
        taxonomy_port: TaxonomyClassificationSessionTaxonomyPort,
    ) -> None:
        self._taxonomy_port = taxonomy_port

    async def list_children(self, *, parent_id: int | None) -> SessionChildrenResponse:
        children = await self._taxonomy_port.list_children(parent_id=parent_id)
        ordered_children = sorted(children, key=lambda child: (child.name, child.id))
        return SessionChildrenResponse(children=ordered_children)

    async def get_assignment(self, *, node_id: int) -> SessionAssignmentResponse:
        assignment = await self._taxonomy_port.get_assignment_for_node(node_id=node_id)
        return SessionAssignmentResponse(assignment=assignment)

    async def assign_leaf(self, *, node_id: int, leaf_id: int) -> SessionAssignLeafResponse:
        assignment = await self._taxonomy_port.set_current_assignment(
            node_id=node_id,
            taxonomy_node_id=leaf_id,
        )
        return SessionAssignLeafResponse(
            result="assigned",
            assignment=assignment,
        )
