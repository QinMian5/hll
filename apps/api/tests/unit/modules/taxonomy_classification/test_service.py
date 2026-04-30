"""
Abstract: Unit tests for taxonomy-classification batch orchestration semantics.
Out of scope: Real cursor-agent subprocess behavior and database transaction checks.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

import pytest

from modules.knowledge_graph.dto import TaxonomyClassificationNodeInput
from modules.taxonomy.dto import TaxonomyAssignmentRecord, TaxonomyNodeRecord
from modules.taxonomy_classification.service import TaxonomyClassificationService


@dataclass(slots=True)
class _StubKnowledgePort:
    nodes: list[TaxonomyClassificationNodeInput]
    requested_limits: list[int | None] = field(default_factory=list)

    async def list_unassigned_nodes_for_taxonomy_classification(
        self,
        *,
        limit: int | None,
    ) -> list[TaxonomyClassificationNodeInput]:
        self.requested_limits.append(limit)
        if limit is None:
            return list(self.nodes)
        return list(self.nodes[:limit])


@dataclass(slots=True)
class _StubTaxonomyStatusPort:
    assignments: dict[int, TaxonomyAssignmentRecord] = field(default_factory=dict)

    async def get_assignment_for_node(self, *, node_id: int) -> TaxonomyAssignmentRecord | None:
        return self.assignments.get(node_id)


@dataclass(slots=True)
class _StubRunner:
    taxonomy_status_port: _StubTaxonomyStatusPort
    assigned_leaf_id: int = 7
    failed_node_ids: set[int] = field(default_factory=set)

    async def run_node_session(
        self,
        *,
        node: TaxonomyClassificationNodeInput,
    ) -> None:
        if node.node_id in self.failed_node_ids:
            raise RuntimeError(f"node {node.node_id} failed")
        self.taxonomy_status_port.assignments[node.node_id] = TaxonomyAssignmentRecord(
            id=node.node_id + 100,
            node_id=node.node_id,
            taxonomy_node=TaxonomyNodeRecord(
                id=self.assigned_leaf_id,
                parent_id=1,
                name="Leaf",
                route_slug="leaf",
                depth=2,
                is_leaf=True,
            ),
            assigned_at=datetime.now(UTC),
        )


@pytest.mark.anyio
async def test_service_processes_unassigned_nodes_in_id_order_with_limit() -> None:
    nodes = [
        TaxonomyClassificationNodeInput(node_id=1, title="One", content="A"),
        TaxonomyClassificationNodeInput(node_id=2, title="Two", content="B"),
        TaxonomyClassificationNodeInput(node_id=3, title="Three", content="C"),
    ]
    taxonomy_status_port = _StubTaxonomyStatusPort()
    knowledge_port = _StubKnowledgePort(nodes=nodes)
    service = TaxonomyClassificationService(
        knowledge_port=knowledge_port,
        cursor_runner=_StubRunner(taxonomy_status_port=taxonomy_status_port),
        taxonomy_status_port=taxonomy_status_port,
        default_max_workers=8,
    )

    result = await service.classify_unassigned(limit=2, max_workers=8)

    assert result.selected_node_ids == [1, 2]
    assert result.assigned_count == 2
    assert result.error_count == 0


@pytest.mark.anyio
async def test_service_continues_after_single_node_failure() -> None:
    nodes = [
        TaxonomyClassificationNodeInput(node_id=1, title="One", content="A"),
        TaxonomyClassificationNodeInput(node_id=2, title="Two", content="B"),
    ]
    taxonomy_status_port = _StubTaxonomyStatusPort()
    service = TaxonomyClassificationService(
        knowledge_port=_StubKnowledgePort(nodes=nodes),
        cursor_runner=_StubRunner(
            taxonomy_status_port=taxonomy_status_port,
            failed_node_ids={2},
        ),
        taxonomy_status_port=taxonomy_status_port,
        default_max_workers=8,
    )

    result = await service.classify_unassigned(limit=2, max_workers=8)

    assert result.selected_count == 2
    assert result.assigned_count == 1
    assert result.unchanged_count == 0
    assert result.error_count == 1
    assert [outcome.node_id for outcome in result.outcomes] == [1, 2]


@pytest.mark.anyio
async def test_service_uses_all_when_limit_is_missing() -> None:
    knowledge_port = _StubKnowledgePort(
        nodes=[
            TaxonomyClassificationNodeInput(node_id=4, title="Four", content="D"),
            TaxonomyClassificationNodeInput(node_id=5, title="Five", content="E"),
        ]
    )
    taxonomy_status_port = _StubTaxonomyStatusPort()
    service = TaxonomyClassificationService(
        knowledge_port=knowledge_port,
        cursor_runner=_StubRunner(taxonomy_status_port=taxonomy_status_port),
        taxonomy_status_port=taxonomy_status_port,
        default_max_workers=8,
    )

    result = await service.classify_unassigned(limit=None, max_workers=8)

    assert knowledge_port.requested_limits == [None]
    assert result.selected_node_ids == [4, 5]
