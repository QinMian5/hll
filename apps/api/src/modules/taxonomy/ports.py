"""
Abstract: Dependency contracts for taxonomy bootstrap import orchestration.
Out of scope: SQLAlchemy repository implementation and HTTP transport wiring.
"""

from __future__ import annotations

from typing import Protocol


class TaxonomyImportPort(Protocol):
    async def has_any_taxonomy_nodes(self) -> bool: ...

    async def create_taxonomy_node(
        self,
        *,
        parent_id: int | None,
        name: str,
        depth: int,
        is_leaf: bool,
    ) -> int: ...

    async def commit(self) -> None: ...

    async def rollback(self) -> None: ...
