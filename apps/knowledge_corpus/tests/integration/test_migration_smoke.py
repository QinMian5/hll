"""
Abstract: Integration smoke tests validating isolated Wikipedia schema migration bootstrap.
Out of scope: Repository query behavior and processed-document business workflows.
"""

from __future__ import annotations

import pytest
from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import AsyncEngine


@pytest.mark.integration
@pytest.mark.db
@pytest.mark.migration
@pytest.mark.anyio
async def test_knowledge_corpus_migration_creates_wikipedia_tables(
    db_engine: AsyncEngine,
) -> None:
    async with db_engine.connect() as connection:
        tables = await connection.run_sync(
            lambda sync_connection: inspect(sync_connection).get_table_names(schema="wikipedia")
        )

    assert tables == ["documents", "processed_documents"]
