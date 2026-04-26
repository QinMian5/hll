"""
Abstract: Integration tests for persisted taxonomy root integrity constraints.
Out of scope: Taxonomy import orchestration and HTTP view contracts.
"""

from __future__ import annotations

import pytest
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from modules.taxonomy.model import TaxonomyNode

pytestmark = [pytest.mark.integration, pytest.mark.db, pytest.mark.anyio]


async def test_storage_rejects_second_root_row(db_session: AsyncSession) -> None:
    db_session.add(TaxonomyNode(parent_id=None, name="Root", depth=0, is_leaf=False))
    await db_session.flush()

    db_session.add(TaxonomyNode(parent_id=None, name="Root", depth=0, is_leaf=False))

    with pytest.raises(DBAPIError):
        await db_session.flush()


async def test_storage_leaves_root_shape_to_business_layer(db_session: AsyncSession) -> None:
    db_session.add(TaxonomyNode(parent_id=None, name="Science", depth=0, is_leaf=False))

    await db_session.flush()
