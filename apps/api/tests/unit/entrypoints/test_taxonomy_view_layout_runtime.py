"""
Abstract: Unit tests for the taxonomy view layout background runtime loop unit.
Out of scope: Redis server integration, SQLAlchemy engine wiring, and Docker
entrypoint scripts.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field

import pytest

from entrypoints.taxonomy_view_layout_runtime import process_next_leaf_layout


@dataclass(slots=True)
class _FakeLayoutCache:
    claimed_leaf_id: int | None
    completed_leaf_ids: list[int] = field(default_factory=list)

    async def claim_leaf_layout_compute(self) -> int | None:
        return self.claimed_leaf_id

    async def complete_leaf_layout_compute(self, *, leaf_id: int) -> None:
        self.completed_leaf_ids.append(leaf_id)


@dataclass(slots=True)
class _FakeTaxonomyService:
    computed_leaf_ids: list[int] = field(default_factory=list)
    fail: bool = False

    async def build_and_cache_leaf_layout(self, *, leaf_id: int) -> None:
        self.computed_leaf_ids.append(leaf_id)
        if self.fail:
            raise RuntimeError("layout compute failed")


@pytest.mark.anyio
async def test_process_next_leaf_layout_claims_computes_and_completes() -> None:
    cache = _FakeLayoutCache(claimed_leaf_id=9)
    service = _FakeTaxonomyService()

    @asynccontextmanager
    async def service_factory() -> AsyncIterator[_FakeTaxonomyService]:
        yield service

    processed = await process_next_leaf_layout(
        cache=cache,
        service_factory=service_factory,
    )

    assert processed is True
    assert service.computed_leaf_ids == [9]
    assert cache.completed_leaf_ids == [9]


@pytest.mark.anyio
async def test_process_next_leaf_layout_returns_false_when_queue_is_empty() -> None:
    cache = _FakeLayoutCache(claimed_leaf_id=None)

    @asynccontextmanager
    async def service_factory() -> AsyncIterator[_FakeTaxonomyService]:
        raise AssertionError("service factory should not be opened")
        yield _FakeTaxonomyService()

    processed = await process_next_leaf_layout(
        cache=cache,
        service_factory=service_factory,
    )

    assert processed is False
    assert cache.completed_leaf_ids == []


@pytest.mark.anyio
async def test_process_next_leaf_layout_completes_singleflight_state_after_failure() -> None:
    cache = _FakeLayoutCache(claimed_leaf_id=9)
    service = _FakeTaxonomyService(fail=True)

    @asynccontextmanager
    async def service_factory() -> AsyncIterator[_FakeTaxonomyService]:
        yield service

    processed = await process_next_leaf_layout(
        cache=cache,
        service_factory=service_factory,
    )

    assert processed is True
    assert service.computed_leaf_ids == [9]
    assert cache.completed_leaf_ids == [9]
