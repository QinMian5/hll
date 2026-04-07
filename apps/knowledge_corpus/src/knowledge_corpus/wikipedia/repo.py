"""
Abstract: Async repository primitives for Wikipedia document persistence.
Out of scope: File-system orchestration and keyword ranking semantics.
"""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import Select, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from knowledge_corpus.wikipedia.model import WikipediaDocument, WikipediaProcessedDocument
from knowledge_corpus.wikipedia.types import (
    WikipediaDocumentRecord,
    WikipediaProcessedDocumentRecord,
)


async def upsert_documents(
    session: AsyncSession,
    records: Sequence[WikipediaDocumentRecord],
) -> None:
    if not records:
        return

    deduplicated_records = {record.page_id: record for record in records}

    statement = insert(WikipediaDocument).values(
        [
            {
                "page_id": record.page_id,
                "url": record.url,
                "title": record.title,
                "clean_text": record.clean_text,
            }
            for record in deduplicated_records.values()
        ]
    )
    statement = statement.on_conflict_do_update(
        index_elements=[WikipediaDocument.page_id],
        set_={
            "url": statement.excluded.url,
            "title": statement.excluded.title,
            "clean_text": statement.excluded.clean_text,
        },
        where=or_(
            WikipediaDocument.url.is_distinct_from(statement.excluded.url),
            WikipediaDocument.title.is_distinct_from(statement.excluded.title),
            WikipediaDocument.clean_text.is_distinct_from(statement.excluded.clean_text),
        ),
    )
    await session.execute(statement)


async def upsert_processed_document(
    session: AsyncSession,
    *,
    page_id: int,
    external_target_ref: str,
) -> None:
    statement = insert(WikipediaProcessedDocument).values(
        {
            "page_id": page_id,
            "external_target_ref": external_target_ref,
        }
    )
    statement = statement.on_conflict_do_update(
        index_elements=[WikipediaProcessedDocument.page_id],
        set_={
            "external_target_ref": statement.excluded.external_target_ref,
        },
    )
    await session.execute(statement)


def select_processed_documents() -> Select[tuple[WikipediaProcessedDocument]]:
    return select(WikipediaProcessedDocument)


async def fetch_processed_documents(
    session: AsyncSession,
) -> list[WikipediaProcessedDocumentRecord]:
    rows = await session.scalars(select_processed_documents())
    return [
        WikipediaProcessedDocumentRecord(
            page_id=row.page_id,
            processed_at=row.processed_at,
            external_target_ref=row.external_target_ref,
        )
        for row in rows
    ]
