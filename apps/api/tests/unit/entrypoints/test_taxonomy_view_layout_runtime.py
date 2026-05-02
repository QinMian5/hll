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

from entrypoints.taxonomy_view_layout_runtime import process_next_card_scope_layout
from modules.taxonomy.dto import TaxonomyScopeIdentity
from modules.taxonomy.repo import TAXONOMY_NODE_SCOPE_KIND


@dataclass(slots=True)
class _FakeLayoutCache:
    claimed_scope_identity: TaxonomyScopeIdentity | None
    completed_scope_identities: list[TaxonomyScopeIdentity] = field(default_factory=list)

    async def claim_card_scope_layout_compute(self) -> TaxonomyScopeIdentity | None:
        return self.claimed_scope_identity

    async def complete_card_scope_layout_compute(
        self,
        *,
        scope_identity: TaxonomyScopeIdentity,
    ) -> None:
        self.completed_scope_identities.append(scope_identity)


@dataclass(slots=True)
class _FakeTaxonomyService:
    computed_scope_identities: list[TaxonomyScopeIdentity] = field(default_factory=list)
    fail: bool = False

    async def build_and_cache_card_scope_layout(
        self,
        *,
        scope_identity: TaxonomyScopeIdentity,
    ) -> None:
        self.computed_scope_identities.append(scope_identity)
        if self.fail:
            raise RuntimeError("layout compute failed")


@pytest.mark.anyio
async def test_process_next_card_scope_layout_claims_computes_and_completes() -> None:
    scope_identity = TaxonomyScopeIdentity(
        scope_kind=TAXONOMY_NODE_SCOPE_KIND,
        taxonomy_node_id=9,
    )
    cache = _FakeLayoutCache(claimed_scope_identity=scope_identity)
    service = _FakeTaxonomyService()

    @asynccontextmanager
    async def service_factory() -> AsyncIterator[_FakeTaxonomyService]:
        yield service

    processed = await process_next_card_scope_layout(
        cache=cache,
        service_factory=service_factory,
    )

    assert processed is True
    assert service.computed_scope_identities == [scope_identity]
    assert cache.completed_scope_identities == [scope_identity]


@pytest.mark.anyio
async def test_process_next_card_scope_layout_returns_false_when_queue_is_empty() -> None:
    cache = _FakeLayoutCache(claimed_scope_identity=None)

    @asynccontextmanager
    async def service_factory() -> AsyncIterator[_FakeTaxonomyService]:
        raise AssertionError("service factory should not be opened")
        yield _FakeTaxonomyService()

    processed = await process_next_card_scope_layout(
        cache=cache,
        service_factory=service_factory,
    )

    assert processed is False
    assert cache.completed_scope_identities == []


@pytest.mark.anyio
async def test_process_next_card_scope_layout_completes_singleflight_state_after_failure() -> None:
    scope_identity = TaxonomyScopeIdentity(
        scope_kind=TAXONOMY_NODE_SCOPE_KIND,
        taxonomy_node_id=9,
    )
    cache = _FakeLayoutCache(claimed_scope_identity=scope_identity)
    service = _FakeTaxonomyService(fail=True)

    @asynccontextmanager
    async def service_factory() -> AsyncIterator[_FakeTaxonomyService]:
        yield service

    processed = await process_next_card_scope_layout(
        cache=cache,
        service_factory=service_factory,
    )

    assert processed is True
    assert service.computed_scope_identities == [scope_identity]
    assert cache.completed_scope_identities == [scope_identity]
