"""
Abstract: Unit tests for taxonomy layout precompute operator orchestration.
Out of scope: Database, Redis, and layout solver integration.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field

import pytest

from entrypoints.ops import taxonomy_layout_precompute as precompute
from modules.taxonomy.dto import (
    TaxonomyCardScopePrecomputeResult,
    TaxonomyCardScopePrecomputeTarget,
    TaxonomyScopeIdentity,
)
from modules.taxonomy.repo import TAXONOMY_NODE_SCOPE_KIND


@dataclass(slots=True)
class _FakePrecomputeService:
    target: TaxonomyCardScopePrecomputeTarget
    statuses: list[str]
    prepare_calls: int = 0

    async def list_card_scope_precompute_targets(
        self,
    ) -> list[TaxonomyCardScopePrecomputeTarget]:
        return [self.target]

    async def prepare_card_scope_layout_precompute_target(
        self,
        *,
        target: TaxonomyCardScopePrecomputeTarget,
    ) -> TaxonomyCardScopePrecomputeResult:
        status = self.statuses[min(self.prepare_calls, len(self.statuses) - 1)]
        self.prepare_calls += 1
        return TaxonomyCardScopePrecomputeResult(
            target=target,
            status=status,
            input_fingerprint="abc123",
            error_message="layout failed" if status == "failed" else None,
        )


@dataclass(slots=True)
class _Processor:
    service: _FakePrecomputeService
    calls: int = 0
    processed_results: list[bool] = field(default_factory=lambda: [True])

    async def __call__(
        self,
        *,
        service_factory: precompute.TaxonomyPrecomputeServiceFactory,
    ) -> bool:
        self.calls += 1
        return self.processed_results[min(self.calls - 1, len(self.processed_results) - 1)]


def _target() -> TaxonomyCardScopePrecomputeTarget:
    return TaxonomyCardScopePrecomputeTarget(
        scope_identity=TaxonomyScopeIdentity(
            scope_kind=TAXONOMY_NODE_SCOPE_KIND,
            taxonomy_node_id=9,
        ),
        route_path="science/heat",
        name="Heat",
    )


def _service_factory(
    service: _FakePrecomputeService,
) -> precompute.TaxonomyPrecomputeServiceFactory:
    @asynccontextmanager
    async def factory() -> AsyncIterator[_FakePrecomputeService]:
        yield service

    return factory


@pytest.mark.anyio
async def test_queue_only_precompute_prepares_targets_without_runtime_processing() -> None:
    service = _FakePrecomputeService(target=_target(), statuses=["queued"])
    processor = _Processor(service=service)

    run = await precompute.run_precompute(
        service_factory=_service_factory(service),
        process_next=processor,
        options=precompute.TaxonomyLayoutPrecomputeOptions(wait=False),
    )

    assert processor.calls == 0
    assert run.timed_out is False
    assert run.summary.total == 1
    assert run.summary.queued == 1
    assert precompute.exit_code_for_run(run) == 0


@pytest.mark.anyio
async def test_wait_precompute_uses_runtime_processing_until_targets_are_ready() -> None:
    service = _FakePrecomputeService(target=_target(), statuses=["queued", "ready"])
    processor = _Processor(service=service)

    run = await precompute.run_precompute(
        service_factory=_service_factory(service),
        process_next=processor,
        options=precompute.TaxonomyLayoutPrecomputeOptions(
            wait=True,
            timeout_seconds=10.0,
            poll_interval_seconds=0.0,
        ),
    )

    assert processor.calls == 1
    assert run.timed_out is False
    assert run.summary.ready == 1
    assert precompute.exit_code_for_run(run) == 0


@pytest.mark.anyio
async def test_wait_precompute_uses_worker_count_for_runtime_processing() -> None:
    service = _FakePrecomputeService(target=_target(), statuses=["queued", "ready"])
    processor = _Processor(service=service)

    run = await precompute.run_precompute(
        service_factory=_service_factory(service),
        process_next=processor,
        options=precompute.TaxonomyLayoutPrecomputeOptions(
            wait=True,
            workers=2,
            timeout_seconds=10.0,
            poll_interval_seconds=0.0,
        ),
    )

    assert processor.calls == 2
    assert run.summary.ready == 1
    assert precompute.exit_code_for_run(run) == 0


@pytest.mark.anyio
async def test_wait_precompute_reports_progress_after_each_summary_refresh() -> None:
    service = _FakePrecomputeService(target=_target(), statuses=["queued", "ready"])
    processor = _Processor(service=service)
    progress: list[tuple[int, int, int, int]] = []

    await precompute.run_precompute(
        service_factory=_service_factory(service),
        process_next=processor,
        options=precompute.TaxonomyLayoutPrecomputeOptions(
            wait=True,
            timeout_seconds=10.0,
            poll_interval_seconds=0.0,
        ),
        progress_reporter=lambda summary: progress.append(
            (summary.ready, summary.queued, summary.refreshing, summary.failed)
        ),
    )

    assert progress == [(0, 1, 0, 0), (1, 0, 0, 0)]


@pytest.mark.anyio
async def test_wait_precompute_times_out_when_targets_do_not_become_ready() -> None:
    service = _FakePrecomputeService(target=_target(), statuses=["queued"])
    processor = _Processor(service=service, processed_results=[False])

    run = await precompute.run_precompute(
        service_factory=_service_factory(service),
        process_next=processor,
        options=precompute.TaxonomyLayoutPrecomputeOptions(
            wait=True,
            timeout_seconds=0.0,
            poll_interval_seconds=0.0,
        ),
    )

    assert run.timed_out is True
    assert run.summary.queued == 1
    assert precompute.exit_code_for_run(run) == 1


@pytest.mark.anyio
async def test_failed_target_makes_precompute_exit_nonzero() -> None:
    service = _FakePrecomputeService(target=_target(), statuses=["failed"])
    processor = _Processor(service=service)

    run = await precompute.run_precompute(
        service_factory=_service_factory(service),
        process_next=processor,
        options=precompute.TaxonomyLayoutPrecomputeOptions(wait=True),
    )

    assert run.timed_out is False
    assert run.summary.failed == 1
    assert run.summary.results[0].target.route_path == "science/heat"
    assert run.summary.results[0].error_message == "layout failed"
    assert precompute.exit_code_for_run(run) == 1
