"""
Abstract: Unit tests for semantic-map repository boundary behavior.
Out of scope: Database I/O, transaction management, and SQL runtime integration.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from modules.semantic_map.repo import SemanticMapRepo


@dataclass(slots=True)
class _StubSession:
    scalar_calls: list[object] = field(default_factory=list)

    async def scalar(self, statement: object) -> object | None:
        self.scalar_calls.append(statement)
        return None


@pytest.mark.anyio
async def test_repo_returns_none_when_no_current_snapshot() -> None:
    session = _StubSession()
    repo = SemanticMapRepo(session=session)

    assert await repo.get_current_manifest() is None
    assert len(session.scalar_calls) == 1
