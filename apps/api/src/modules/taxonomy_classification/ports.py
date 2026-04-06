"""
Abstract: Dependency contracts for taxonomy-classification orchestration services.
Out of scope: HTTP command parsing and concrete infrastructure composition.
"""

from __future__ import annotations

from typing import Protocol

from modules.knowledge_graph.dto import TaxonomyClassificationNodeInput
from modules.taxonomy.dto import TaxonomyAssignmentRecord, TaxonomyNodeRecord


class TaxonomyClassificationKnowledgePort(Protocol):
    async def list_unassigned_nodes_for_taxonomy_classification(
        self,
        *,
        limit: int | None,
    ) -> list[TaxonomyClassificationNodeInput]: ...


class CursorClassificationRunnerPort(Protocol):
    async def run_node_session(
        self,
        *,
        node: TaxonomyClassificationNodeInput,
    ) -> None: ...


class TaxonomyClassificationStatusPort(Protocol):
    async def get_assignment_for_node(self, *, node_id: int) -> TaxonomyAssignmentRecord | None: ...


class TaxonomyClassificationSessionTaxonomyPort(Protocol):
    async def list_children(self, *, parent_id: int | None) -> list[TaxonomyNodeRecord]: ...

    async def get_assignment_for_node(self, *, node_id: int) -> TaxonomyAssignmentRecord | None: ...

    async def set_final_assignment(
        self,
        *,
        node_id: int,
        taxonomy_node_id: int,
    ) -> TaxonomyAssignmentRecord: ...
