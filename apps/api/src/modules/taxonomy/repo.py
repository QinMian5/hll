"""
Abstract: Async SQLAlchemy repository primitives for taxonomy bootstrap import and tree persistence.
Out of scope: YAML parsing and HTTP transport wiring.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from modules.taxonomy.model import TaxonomyNode


class TaxonomyRepo:
    def __init__(self, *, session: AsyncSession) -> None:
        self._session = session

    async def has_any_taxonomy_nodes(self) -> bool:
        result = await self._session.execute(select(TaxonomyNode.id).limit(1))
        return result.scalar_one_or_none() is not None

    async def create_taxonomy_node(
        self,
        *,
        parent_id: int | None,
        name: str,
        depth: int,
        is_leaf: bool,
    ) -> int:
        taxonomy_node = TaxonomyNode(
            parent_id=parent_id,
            name=name,
            depth=depth,
            is_leaf=is_leaf,
        )
        self._session.add(taxonomy_node)
        await self._session.flush()
        return taxonomy_node.id

    async def commit(self) -> None:
        await self._session.commit()

    async def rollback(self) -> None:
        await self._session.rollback()
