"""
Abstract: Integration smoke tests validating isolated Wikipedia schema migration bootstrap.
Out of scope: Repository query behavior and processed-document business workflows.
"""

from __future__ import annotations

import pytest
from sqlalchemy import inspect
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import AsyncEngine


@pytest.mark.integration
@pytest.mark.db
@pytest.mark.migration
@pytest.mark.anyio
async def test_knowledge_corpus_migration_creates_wikipedia_tables(
    db_engine: AsyncEngine,
) -> None:
    async with db_engine.connect() as connection:

        def _inspect_schema(
            sync_connection: Connection,
        ) -> tuple[list[str], list[dict[str, object]]]:
            inspector = inspect(sync_connection)
            return (
                inspector.get_table_names(schema="wikipedia"),
                inspector.get_columns("documents", schema="wikipedia"),
            )

        tables, document_columns = await connection.run_sync(_inspect_schema)

    assert sorted(tables) == ["documents", "processed_documents"]
    title_column = next(column for column in document_columns if column["name"] == "title")
    assert str(title_column["type"]).upper() == "TEXT"
