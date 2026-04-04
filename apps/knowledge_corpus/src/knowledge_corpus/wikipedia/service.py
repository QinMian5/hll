"""
Abstract: High-level async service helpers for Wikipedia corpus operations.
Out of scope: File traversal and caller-specific orchestration workflows.
"""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from knowledge_corpus.wikipedia import repo, search
from knowledge_corpus.wikipedia.types import WikipediaDocumentRecord, WikipediaSearchResult


async def upsert_documents(
    session: AsyncSession,
    records: Sequence[WikipediaDocumentRecord],
) -> None:
    await repo.upsert_documents(session, records)


async def mark_document_processed(
    session: AsyncSession,
    *,
    page_id: int,
    external_target_ref: str,
) -> None:
    await repo.upsert_processed_document(
        session,
        page_id=page_id,
        external_target_ref=external_target_ref,
    )


async def search_documents(
    session: AsyncSession,
    *,
    query: str,
    exclude_processed: bool,
    limit: int,
) -> list[WikipediaSearchResult]:
    return await search.search_documents(
        session,
        query=query,
        exclude_processed=exclude_processed,
        limit=limit,
    )


async def list_unprocessed_documents(
    session: AsyncSession,
    *,
    query: str,
    limit: int,
) -> list[WikipediaSearchResult]:
    return await search.list_unprocessed_documents(
        session,
        query=query,
        limit=limit,
    )
