"""
Abstract: Integration tests for high-level Wikipedia service helpers.
Out of scope: Full-text SQL shape and compose bootstrap.
"""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from knowledge_corpus.wikipedia.service import (
    list_unprocessed_documents,
    mark_document_processed,
    upsert_documents,
)
from knowledge_corpus.wikipedia.types import WikipediaDocumentRecord

pytestmark = [pytest.mark.integration, pytest.mark.db, pytest.mark.anyio]


async def test_list_unprocessed_documents_filters_processed_rows(
    db_session: AsyncSession,
) -> None:
    processed = WikipediaDocumentRecord(
        page_id=301,
        url="https://en.wikipedia.org/wiki/Algebra",
        title="Algebra",
        clean_text="Algebra studies variables and equations.",
    )
    pending = WikipediaDocumentRecord(
        page_id=302,
        url="https://en.wikipedia.org/wiki/Topology",
        title="Topology",
        clean_text="Topology studies continuity and deformation.",
    )

    await upsert_documents(db_session, [processed, pending])
    await mark_document_processed(
        db_session,
        page_id=processed.page_id,
        external_target_ref="node:301",
    )
    await db_session.commit()

    results = await list_unprocessed_documents(
        db_session,
        query="studies",
        limit=10,
    )

    assert [item.page_id for item in results] == [302]
