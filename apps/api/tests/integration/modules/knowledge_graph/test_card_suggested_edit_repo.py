"""
Abstract: Database-backed repository tests for card suggested edit persistence.
Out of scope: HTTP route wiring and suggestion review workflows.
"""

from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from modules.knowledge_graph.model import CardSuggestedEdit, CardVersion, Node
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


async def test_create_card_suggested_edit_persists_pending_row(
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
    )

    stored = await db_session.scalar(
        select(CardSuggestedEdit).where(CardSuggestedEdit.id == record.id)
    )
    assert stored is not None
    assert record.status == "pending"
    assert stored.node_id == node.id
    assert stored.base_version == 1
    assert stored.suggested_by_user_id == "logto-user-123"


async def test_create_card_suggested_edit_requires_existing_base_version(
    db_session: AsyncSession,
) -> None:
    node, _ = await _create_card_version(db_session, version=1)
    repo = KnowledgeRepo(session=db_session)

    with pytest.raises(DBAPIError):
        await repo.create_card_suggested_edit(
            node_id=node.id,
            base_version=2,
            suggested_title="Better title",
            suggested_content="Better content",
            suggested_by_user_id="logto-user-123",
        )
