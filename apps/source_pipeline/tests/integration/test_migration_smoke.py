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
        "card_candidates",
        "workflow_runs",
        "workflow_units",
    } <= set(tables)
    assert "card_review_jobs" not in set(tables)


@pytest.mark.integration
@pytest.mark.db
@pytest.mark.migration
@pytest.mark.anyio
async def test_source_pipeline_migration_creates_card_candidate_constraints(
    db_engine: AsyncEngine,
) -> None:
    async with db_engine.connect() as connection:

        def _inspect_constraints(sync_connection: Connection) -> set[str]:
            inspector = inspect(sync_connection)
            unique_constraints = inspector.get_unique_constraints("card_candidates")
            return {
                constraint["name"]
                for constraint in unique_constraints
                if constraint["name"] is not None
            }

        constraint_names = await connection.run_sync(_inspect_constraints)

    assert "uq_card_candidates_workflow_origin" in constraint_names
    assert "uq_card_candidates_parent_origin" in constraint_names
