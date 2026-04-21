"""
Abstract: Integration smoke tests validating isolated source-pipeline migration bootstrap.
Out of scope: Queue interaction and runtime orchestration behavior.
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
async def test_source_pipeline_migration_creates_expected_tables(
    db_engine: AsyncEngine,
) -> None:
    async with db_engine.connect() as connection:

        def _inspect_tables(sync_connection: Connection) -> list[str]:
            inspector = inspect(sync_connection)
            return inspector.get_table_names()

        tables = await connection.run_sync(_inspect_tables)

    assert {
        "alembic_version",
        "card_review_jobs",
        "workflow_runs",
        "workflow_units",
    } <= set(tables)
