"""
Abstract: Integration tests for taxonomy bootstrap import against PostgreSQL-backed storage.
Out of scope: Trigger enforcement and operator-script invocation.
"""

from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from modules.taxonomy.errors import TaxonomyImportError
from modules.taxonomy.importer import TaxonomyImporter
from modules.taxonomy.model import TaxonomyNode
from modules.taxonomy.repo import TaxonomyRepo

_SAMPLE_LCC_YAML = """
Science:
  - Mathematics:
      - General
      - Algebra
"""


@pytest.mark.integration
@pytest.mark.db
@pytest.mark.anyio
async def test_importer_persists_depth_and_leaf_flags_into_empty_store(
    db_session: AsyncSession,
) -> None:
    importer = TaxonomyImporter(repo=TaxonomyRepo(session=db_session))

    imported_count = await importer.import_yaml_text(_SAMPLE_LCC_YAML)

    result = await db_session.execute(
        select(TaxonomyNode).order_by(TaxonomyNode.depth.asc(), TaxonomyNode.name.asc())
    )
    rows = list(result.scalars())

    assert imported_count == 4
    assert [(row.name, row.depth, row.is_leaf) for row in rows] == [
        ("Science", 0, False),
        ("Mathematics", 1, False),
        ("Algebra", 2, True),
        ("General", 2, True),
    ]


@pytest.mark.integration
@pytest.mark.db
@pytest.mark.anyio
async def test_importer_fails_when_taxonomy_store_is_not_empty(
    db_session: AsyncSession,
) -> None:
    db_session.add(
        TaxonomyNode(
            parent_id=None,
            name="Existing",
            depth=0,
            is_leaf=True,
        )
    )
    await db_session.flush()

    importer = TaxonomyImporter(repo=TaxonomyRepo(session=db_session))

    with pytest.raises(TaxonomyImportError, match="already contains"):
        await importer.import_yaml_text(_SAMPLE_LCC_YAML)
