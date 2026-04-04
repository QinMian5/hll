"""
Abstract: Integration tests for Wikipedia keyword retrieval behavior.
Out of scope: Bulk import orchestration and migration bootstrap.
"""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from knowledge_corpus.wikipedia.service import (
    mark_document_processed,
    search_documents,
    upsert_documents,
)
from knowledge_corpus.wikipedia.types import WikipediaDocumentRecord

pytestmark = [pytest.mark.integration, pytest.mark.db, pytest.mark.anyio]


def _physics_record() -> WikipediaDocumentRecord:
    return WikipediaDocumentRecord(
        page_id=100,
        url="https://en.wikipedia.org/wiki/Physics",
        title="Physics",
        clean_text="Physics studies matter, energy, space, and time.",
    )


def _chemistry_record() -> WikipediaDocumentRecord:
    return WikipediaDocumentRecord(
        page_id=101,
        url="https://en.wikipedia.org/wiki/Chemistry",
        title="Chemistry",
        clean_text="Chemistry studies atoms, molecules, and reactions.",
    )


async def test_search_documents_excludes_processed_rows(db_session: AsyncSession) -> None:
    physics = _physics_record()
    chemistry = _chemistry_record()
    await upsert_documents(db_session, [physics, chemistry])
    await mark_document_processed(
        db_session,
        page_id=physics.page_id,
        external_target_ref="node:1",
    )
    await db_session.commit()

    results = await search_documents(
        db_session,
        query="physics",
        exclude_processed=True,
        limit=10,
    )

    assert [item.page_id for item in results] == []


async def test_search_documents_prefers_title_matches(db_session: AsyncSession) -> None:
    title_match = WikipediaDocumentRecord(
        page_id=200,
        url="https://en.wikipedia.org/wiki/Quantum_mechanics",
        title="Quantum mechanics",
        clean_text="An introduction to physics.",
    )
    body_match = WikipediaDocumentRecord(
        page_id=201,
        url="https://en.wikipedia.org/wiki/History_of_science",
        title="History of science",
        clean_text="Quantum mechanics transformed modern physics.",
    )
    await upsert_documents(db_session, [body_match, title_match])
    await db_session.commit()

    results = await search_documents(
        db_session,
        query="quantum mechanics",
        exclude_processed=False,
        limit=10,
    )

    assert [item.page_id for item in results[:2]] == [200, 201]
