"""
Abstract: Integration smoke tests validating isolated PostgreSQL runtime access.
Out of scope: Domain-level repository behavior and API route orchestration.
"""

from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.integration
@pytest.mark.db
@pytest.mark.anyio
async def test_db_session_can_execute_simple_query(db_session: AsyncSession) -> None:
    result = await db_session.execute(text("SELECT 1"))
    assert result.scalar_one() == 1


@pytest.mark.integration
@pytest.mark.db
@pytest.mark.migration
@pytest.mark.anyio
async def test_alembic_version_table_exists_after_migration(
    db_session: AsyncSession,
) -> None:
    result = await db_session.execute(
        text("SELECT to_regclass('public.alembic_version')")
    )
    assert result.scalar_one() == "alembic_version"
