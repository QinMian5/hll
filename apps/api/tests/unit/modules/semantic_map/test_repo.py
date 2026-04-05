"""
Abstract: Unit tests for semantic-map repository boundary behavior.
Out of scope: Database I/O, transaction management, and SQL runtime integration.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import cast

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from modules.semantic_map.persistence.repo import SemanticMapRepo


@dataclass(slots=True)
class _StubSession:
    scalar_calls: list[object] = field(default_factory=list)

    async def scalar(self, statement: object) -> object | None:
        self.scalar_calls.append(statement)
        return None


@pytest.mark.anyio
async def test_repo_returns_none_when_no_current_snapshot() -> None:
    stub_session = _StubSession()
    repo = SemanticMapRepo(session=cast(AsyncSession, stub_session))

    assert await repo.get_current_manifest() is None
    assert len(stub_session.scalar_calls) == 1
