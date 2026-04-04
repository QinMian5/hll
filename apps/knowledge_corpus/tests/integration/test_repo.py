"""
Abstract: Integration tests for Wikipedia repository persistence behavior.
Out of scope: Search ranking behavior and architecture boundary enforcement.
"""

from __future__ import annotations

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from knowledge_corpus.wikipedia.model import WikipediaDocument, WikipediaProcessedDocument
from knowledge_corpus.wikipedia.service import mark_document_processed, upsert_documents
from knowledge_corpus.wikipedia.types import WikipediaDocumentRecord

pytestmark = [pytest.mark.integration, pytest.mark.db, pytest.mark.anyio]


def _physics_record() -> WikipediaDocumentRecord:
    return WikipediaDocumentRecord(
        page_id=42,
        url="https://en.wikipedia.org/wiki/Physics",
        title="Physics",
        clean_text="Physics studies matter, energy, motion, and force.",
    )


async def _count_documents(session: AsyncSession) -> int:
    return await session.scalar(select(func.count()).select_from(WikipediaDocument)) or 0


async def _count_processed(session: AsyncSession) -> int:
    return await session.scalar(select(func.count()).select_from(WikipediaProcessedDocument)) or 0


async def test_upsert_documents_is_idempotent(db_session: AsyncSession) -> None:
    record = _physics_record()

    await upsert_documents(db_session, [record, record])
    await db_session.flush()

    assert await _count_documents(db_session) == 1


async def test_mark_processed_is_idempotent(db_session: AsyncSession) -> None:
    record = _physics_record()
    await upsert_documents(db_session, [record])

    await mark_document_processed(
        db_session,
        page_id=record.page_id,
        external_target_ref="node:42",
    )
    await mark_document_processed(
        db_session,
        page_id=record.page_id,
        external_target_ref="node:42",
    )
    await db_session.flush()

    assert await _count_processed(db_session) == 1
