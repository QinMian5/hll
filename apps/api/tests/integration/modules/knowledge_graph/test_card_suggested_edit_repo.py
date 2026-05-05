"""
Abstract: Database-backed repository tests for card proposal persistence.
Out of scope: HTTP route wiring and suggestion review workflows.
"""

from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from modules.knowledge_graph.model import CardProposal, CardVersion, Node
from modules.knowledge_graph.repo import KnowledgeRepo

pytestmark = [pytest.mark.integration, pytest.mark.db, pytest.mark.anyio]


async def _create_card_version(
    db_session: AsyncSession,
    *,
    version: int = 1,
) -> tuple[Node, CardVersion]:
    node = Node(
        title="Base title",
        content="Base content",
        embedding=[0.1] * 1536,
    )
    db_session.add(node)
    await db_session.flush()
    card_version = CardVersion(
        node_id=node.id,
        version=version,
        title=node.title,
        content=node.content,
    )
    db_session.add(card_version)
    await db_session.flush()
    return node, card_version


async def test_create_card_suggested_edit_persists_unified_pending_proposal(
    db_session: AsyncSession,
) -> None:
    node, card_version = await _create_card_version(db_session, version=1)
    repo = KnowledgeRepo(session=db_session)

    record = await repo.create_card_suggested_edit(
        node_id=node.id,
        base_version=card_version.version,
        suggested_title="Better title",
        suggested_content="Better content",
        suggested_by_user_id="logto-user-123",
        reason="The current card needs clearer wording.",
    )

    stored = await db_session.scalar(select(CardProposal).where(CardProposal.id == record.id))
    assert stored is not None
    assert record.status == "pending"
    assert stored.proposal_type == "edit"
    assert stored.status == "pending_review"
    assert stored.submitted_by_user_id == "logto-user-123"
    assert stored.reason == "The current card needs clearer wording."
    assert stored.payload == {
        "target_node_id": node.id,
        "base_version": 1,
        "suggested_title": "Better title",
        "suggested_content": "Better content",
    }


async def test_mark_card_proposal_withdrawn_returns_updated_record(
    db_session: AsyncSession,
) -> None:
    repo = KnowledgeRepo(session=db_session)
    created = await repo.create_card_proposal(
        proposal_type="edit",
        submitted_by_user_id="logto-user-123",
        reason="The current card should be cancelled.",
        payload={
            "target_node_id": 1,
            "base_version": 1,
            "suggested_title": "Better title",
            "suggested_content": "Better content",
        },
    )

    record = await repo.mark_card_proposal_withdrawn(proposal_id=created.id)

    stored = await db_session.scalar(select(CardProposal).where(CardProposal.id == record.id))
    assert stored is not None
    assert record.status == "withdrawn"
    assert stored.status == "withdrawn"
    assert record.updated_at is not None


async def test_submit_card_proposal_requires_existing_base_version(
    db_session: AsyncSession,
) -> None:
    node, _ = await _create_card_version(db_session, version=1)
    repo = KnowledgeRepo(session=db_session)

    assert await repo.fetch_card_version(node_id=node.id, version=2) is None
