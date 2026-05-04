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
from modules.taxonomy.dto import TaxonomyCardScopeLayoutComputeClaim, TaxonomyScopeIdentity
from modules.taxonomy.repo import TAXONOMY_NODE_SCOPE_KIND


@dataclass(slots=True)
class _FakeTaxonomyService:
    claimed_scope_identity: TaxonomyScopeIdentity | None
    computed_scope_identities: list[TaxonomyScopeIdentity] = field(default_factory=list)
    completed_scope_identities: list[TaxonomyScopeIdentity] = field(default_factory=list)
    failed_scope_identities: list[TaxonomyScopeIdentity] = field(default_factory=list)
    fail: bool = False

    async def claim_card_scope_layout_compute(self) -> TaxonomyCardScopeLayoutComputeClaim | None:
        if self.claimed_scope_identity is None:
            return None
        return TaxonomyCardScopeLayoutComputeClaim(
            scope_identity=self.claimed_scope_identity,
            input_fingerprint="abc123",
        )

    async def build_and_cache_card_scope_layout(
        self,
        *,
        scope_identity: TaxonomyScopeIdentity,
    ) -> None:
        self.computed_scope_identities.append(scope_identity)
        if self.fail:
            raise RuntimeError("layout compute failed")

    async def complete_card_scope_layout_compute(
        self,
        *,
        scope_identity: TaxonomyScopeIdentity,
    ) -> None:
        self.completed_scope_identities.append(scope_identity)

    async def fail_card_scope_layout_compute(
        self,
        *,
        scope_identity: TaxonomyScopeIdentity,
        error_message: str,
    ) -> None:
        assert error_message == "layout compute failed"
        self.failed_scope_identities.append(scope_identity)


@pytest.mark.anyio
async def test_process_next_card_scope_layout_claims_computes_and_completes() -> None:
    scope_identity = TaxonomyScopeIdentity(
        scope_kind=TAXONOMY_NODE_SCOPE_KIND,
        taxonomy_node_id=9,
    )
    service = _FakeTaxonomyService(claimed_scope_identity=scope_identity)

    @asynccontextmanager
    async def service_factory() -> AsyncIterator[_FakeTaxonomyService]:
        yield service

    processed = await process_next_card_scope_layout(
        service_factory=service_factory,
    )

    assert processed is True
    assert service.computed_scope_identities == [scope_identity]
    assert service.completed_scope_identities == [scope_identity]


@pytest.mark.anyio
async def test_process_next_card_scope_layout_returns_false_when_queue_is_empty() -> None:
    service = _FakeTaxonomyService(claimed_scope_identity=None)

    @asynccontextmanager
    async def service_factory() -> AsyncIterator[_FakeTaxonomyService]:
        yield service

    processed = await process_next_card_scope_layout(
        service_factory=service_factory,
    )

    assert processed is False
    assert service.completed_scope_identities == []


@pytest.mark.anyio
async def test_process_next_card_scope_layout_completes_singleflight_state_after_failure() -> None:
    scope_identity = TaxonomyScopeIdentity(
        scope_kind=TAXONOMY_NODE_SCOPE_KIND,
        taxonomy_node_id=9,
    )
    service = _FakeTaxonomyService(claimed_scope_identity=scope_identity, fail=True)

    @asynccontextmanager
    async def service_factory() -> AsyncIterator[_FakeTaxonomyService]:
        yield service

    processed = await process_next_card_scope_layout(
        service_factory=service_factory,
    )

    assert processed is True
    assert service.computed_scope_identities == [scope_identity]
    assert service.completed_scope_identities == []
    assert service.failed_scope_identities == [scope_identity]
