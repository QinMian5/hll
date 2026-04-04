"""
Abstract: Async PostgreSQL full-text search helpers for Wikipedia documents.
Out of scope: Write-side persistence and external source normalization.
"""

from __future__ import annotations

from sqlalchemy import func, literal, select
from sqlalchemy.ext.asyncio import AsyncSession

from knowledge_corpus.wikipedia.model import WikipediaDocument, WikipediaProcessedDocument
from knowledge_corpus.wikipedia.types import WikipediaSearchResult


async def search_documents(
    session: AsyncSession,
    *,
    query: str,
    exclude_processed: bool,
    limit: int,
) -> list[WikipediaSearchResult]:
    stripped_query = query.strip()
    if not stripped_query:
        return await list_unprocessed_documents(session, query="", limit=limit)

    ts_query = func.websearch_to_tsquery("english", stripped_query)
    rank = func.ts_rank_cd(WikipediaDocument.search_vector, ts_query)

    statement = (
        select(
            WikipediaDocument.page_id,
            WikipediaDocument.url,
            WikipediaDocument.title,
            WikipediaDocument.clean_text,
            rank.label("rank"),
        )
        .where(WikipediaDocument.search_vector.op("@@")(ts_query))
        .order_by(rank.desc(), WikipediaDocument.page_id.asc())
        .limit(limit)
    )
    if exclude_processed:
        statement = statement.where(
            ~select(WikipediaProcessedDocument.page_id)
            .where(WikipediaProcessedDocument.page_id == WikipediaDocument.page_id)
            .exists()
        )

    rows = await session.execute(statement)
    return [
        WikipediaSearchResult(
            page_id=row.page_id,
            url=row.url,
            title=row.title,
            clean_text=row.clean_text,
            rank=float(row.rank),
        )
        for row in rows
    ]


async def list_unprocessed_documents(
    session: AsyncSession,
    *,
    query: str,
    limit: int,
) -> list[WikipediaSearchResult]:
    stripped_query = query.strip()
    if stripped_query:
        return await search_documents(
            session,
            query=stripped_query,
            exclude_processed=True,
            limit=limit,
        )

    statement = (
        select(
            WikipediaDocument.page_id,
            WikipediaDocument.url,
            WikipediaDocument.title,
            WikipediaDocument.clean_text,
            literal(0.0).label("rank"),
        )
        .where(
            ~select(WikipediaProcessedDocument.page_id)
            .where(WikipediaProcessedDocument.page_id == WikipediaDocument.page_id)
            .exists()
        )
        .order_by(WikipediaDocument.page_id.asc())
        .limit(limit)
    )
    rows = await session.execute(statement)
    return [
        WikipediaSearchResult(
            page_id=row.page_id,
            url=row.url,
            title=row.title,
            clean_text=row.clean_text,
            rank=0.0,
        )
        for row in rows
    ]
