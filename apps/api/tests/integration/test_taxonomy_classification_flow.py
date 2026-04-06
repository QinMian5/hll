"""
Abstract: Integration tests for taxonomy-classification orchestration across module boundaries.
Out of scope: Cursor-agent subprocess orchestration and HTTP-triggered job execution.
"""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from modules.knowledge_graph.dto import TaxonomyClassificationNodeInput
from modules.knowledge_graph.model import Node
from modules.knowledge_graph.repo import KnowledgeRepo
from modules.knowledge_graph.service import KnowledgeGraphService
from modules.taxonomy.model import TaxonomyNode
from modules.taxonomy.repo import TaxonomyRepo
from modules.taxonomy.service import TaxonomyService
from modules.taxonomy_classification.service import TaxonomyClassificationService
from modules.taxonomy_classification.session_tool import TaxonomyClassificationSessionTool


async def _create_node(
    db_session: AsyncSession,
    *,
    title: str,
    content: str,
) -> Node:
    node = Node(
        title=title,
        content=content,
        embedding=[0.1] * 1536,
    )
    db_session.add(node)
    await db_session.flush()
    return node


async def _create_taxonomy_node(
    db_session: AsyncSession,
    *,
    name: str,
    depth: int,
    is_leaf: bool,
    parent_id: int | None = None,
) -> TaxonomyNode:
    taxonomy_node = TaxonomyNode(
        parent_id=parent_id,
        name=name,
        depth=depth,
        is_leaf=is_leaf,
    )
    db_session.add(taxonomy_node)
    await db_session.flush()
    return taxonomy_node


@pytest.mark.integration
@pytest.mark.db
@pytest.mark.anyio
async def test_classification_flow_assigns_leaf_and_keeps_failed_node_unassigned(
    db_session: AsyncSession,
) -> None:
    root = await _create_taxonomy_node(db_session, name="Science", depth=0, is_leaf=False)
    leaf = await _create_taxonomy_node(
        db_session,
        name="Mathematics",
        depth=1,
        is_leaf=True,
        parent_id=root.id,
    )
    good_node = await _create_node(db_session, title="Linear Algebra", content="Vector spaces")
    bad_node = await _create_node(db_session, title="Optics", content="Light propagation")

    taxonomy_service = TaxonomyService(repo=TaxonomyRepo(session=db_session))
    session_tool = TaxonomyClassificationSessionTool(taxonomy_port=taxonomy_service)
    knowledge_service = KnowledgeGraphService(
        repo=KnowledgeRepo(session=db_session),
        edge_similarity_top_k=10,
        edge_similarity_min_strength=0.0,
    )

    class _Runner:
        async def run_node_session(
            self,
            *,
            node: TaxonomyClassificationNodeInput,
        ) -> None:
            if node.node_id == bad_node.id:
                raise RuntimeError("cursor-agent failed")
            await session_tool.assign_leaf(node_id=node.node_id, leaf_id=leaf.id)

    service = TaxonomyClassificationService(
        knowledge_port=knowledge_service,
        cursor_runner=_Runner(),
        taxonomy_status_port=taxonomy_service,
        default_max_workers=8,
    )

    result = await service.classify_unassigned(limit=None, max_workers=1)

    assert result.selected_node_ids == [good_node.id, bad_node.id]
    assert result.assigned_count == 1
    assert result.error_count == 1
    good_assignment = await taxonomy_service.get_assignment_for_node(node_id=good_node.id)
    assert good_assignment is not None
    assert good_assignment.taxonomy_node.id == leaf.id
    assert (await taxonomy_service.get_assignment_for_node(node_id=bad_node.id)) is None


@pytest.mark.integration
@pytest.mark.db
@pytest.mark.anyio
async def test_second_assign_leaf_attempt_is_rejected_without_overwrite(
    db_session: AsyncSession,
) -> None:
    root = await _create_taxonomy_node(db_session, name="Science", depth=0, is_leaf=False)
    first_leaf = await _create_taxonomy_node(
        db_session,
        name="Physics",
        depth=1,
        is_leaf=True,
        parent_id=root.id,
    )
    second_leaf = await _create_taxonomy_node(
        db_session,
        name="Chemistry",
        depth=1,
        is_leaf=True,
        parent_id=root.id,
    )
    node = await _create_node(
        db_session,
        title="Classical Mechanics",
        content="Newtonian motion and force.",
    )
    tool = TaxonomyClassificationSessionTool(
        taxonomy_port=TaxonomyService(repo=TaxonomyRepo(session=db_session)),
    )

    first = await tool.assign_leaf(node_id=node.id, leaf_id=first_leaf.id)
    second = await tool.assign_leaf(node_id=node.id, leaf_id=second_leaf.id)

    assert first.result == "assigned"
    assert second.result == "already_assigned"
    assert second.assignment.taxonomy_node.id == first_leaf.id
