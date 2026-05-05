"""
Abstract: Operator CLI for taxonomy card-scope layout precomputation.
Out of scope: Public API routing, scheduling, and alternate layout persistence.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from collections.abc import Awaitable, Callable
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass
from typing import Protocol, cast

from entrypoints.taxonomy_view_layout_runtime import (
    build_runtime,
    open_taxonomy_layout_service,
    process_next_card_scope_layout,
)
from modules.taxonomy.dto import (
    TaxonomyCardScopePrecomputeResult,
    TaxonomyCardScopePrecomputeSummary,
    TaxonomyCardScopePrecomputeTarget,
)


class TaxonomyPrecomputeService(Protocol):
    async def list_card_scope_precompute_targets(
        self,
    ) -> list[TaxonomyCardScopePrecomputeTarget]: ...

    async def prepare_card_scope_layout_precompute_target(
        self,
        *,
        target: TaxonomyCardScopePrecomputeTarget,
    ) -> TaxonomyCardScopePrecomputeResult: ...


TaxonomyPrecomputeServiceFactory = Callable[
    [],
    AbstractAsyncContextManager[TaxonomyPrecomputeService],
]


class TaxonomyLayoutRuntimeProcessor(Protocol):
    async def __call__(
        self,
        *,
        service_factory: TaxonomyPrecomputeServiceFactory,
    ) -> bool: ...


@dataclass(slots=True, frozen=True)
class TaxonomyLayoutPrecomputeOptions:
    wait: bool = False
    timeout_seconds: float = 900.0
    poll_interval_seconds: float = 1.0


@dataclass(slots=True, frozen=True)
class TaxonomyLayoutPrecomputeRun:
    summary: TaxonomyCardScopePrecomputeSummary
    timed_out: bool


async def run_precompute(
    *,
    service_factory: TaxonomyPrecomputeServiceFactory,
    process_next: TaxonomyLayoutRuntimeProcessor,
    options: TaxonomyLayoutPrecomputeOptions,
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    monotonic: Callable[[], float] = time.monotonic,
) -> TaxonomyLayoutPrecomputeRun:
    targets = await _list_targets(service_factory=service_factory)
    summary = await _prepare_targets(service_factory=service_factory, targets=targets)
    if not options.wait:
        return TaxonomyLayoutPrecomputeRun(summary=summary, timed_out=False)

    deadline = monotonic() + options.timeout_seconds
    while summary.ready < summary.total and summary.failed == 0:
        if monotonic() >= deadline:
            return TaxonomyLayoutPrecomputeRun(summary=summary, timed_out=True)

        processed = await process_next(service_factory=service_factory)
        if not processed and options.poll_interval_seconds > 0:
            await sleep(options.poll_interval_seconds)
        summary = await _prepare_targets(service_factory=service_factory, targets=targets)

    return TaxonomyLayoutPrecomputeRun(summary=summary, timed_out=False)


def exit_code_for_run(run: TaxonomyLayoutPrecomputeRun) -> int:
    if run.timed_out or run.summary.failed > 0:
        return 1
    return 0


def format_run(run: TaxonomyLayoutPrecomputeRun, *, as_json: bool) -> str:
    if as_json:
        return json.dumps(
            {
                "timed_out": run.timed_out,
                "summary": run.summary.model_dump(mode="json"),
            },
            sort_keys=True,
        )

    lines = [
        "Taxonomy layout precompute",
        f"  total: {run.summary.total}",
        f"  ready: {run.summary.ready}",
        f"  queued: {run.summary.queued}",
        f"  refreshing: {run.summary.refreshing}",
        f"  failed: {run.summary.failed}",
        f"  timed_out: {str(run.timed_out).lower()}",
    ]
    for result in run.summary.results:
        if result.status != "failed":
            continue
        lines.append(
            "  failure: "
            f"{result.target.route_path} "
            f"{result.target.scope_identity.scope_kind}/"
            f"{result.target.scope_identity.taxonomy_node_id} "
            f"{result.error_message or ''}".rstrip()
        )
    return "\n".join(lines)


async def _list_targets(
    *,
    service_factory: TaxonomyPrecomputeServiceFactory,
) -> list[TaxonomyCardScopePrecomputeTarget]:
    async with service_factory() as service:
        return await service.list_card_scope_precompute_targets()


async def _prepare_targets(
    *,
    service_factory: TaxonomyPrecomputeServiceFactory,
    targets: list[TaxonomyCardScopePrecomputeTarget],
) -> TaxonomyCardScopePrecomputeSummary:
    results: list[TaxonomyCardScopePrecomputeResult] = []
    async with service_factory() as service:
        for target in targets:
            results.append(await service.prepare_card_scope_layout_precompute_target(target=target))
    return _summary_from_results(results)


def _summary_from_results(
    results: list[TaxonomyCardScopePrecomputeResult],
) -> TaxonomyCardScopePrecomputeSummary:
    counts = {"ready": 0, "queued": 0, "refreshing": 0, "failed": 0}
    for result in results:
        counts[result.status] += 1
    return TaxonomyCardScopePrecomputeSummary(
        total=len(results),
        ready=counts["ready"],
        queued=counts["queued"],
        refreshing=counts["refreshing"],
        failed=counts["failed"],
        results=results,
    )


async def _run_with_runtime(
    *,
    options: TaxonomyLayoutPrecomputeOptions,
) -> TaxonomyLayoutPrecomputeRun:
    runtime = build_runtime()
    try:
        return await run_precompute(
            service_factory=lambda: open_taxonomy_layout_service(runtime),
            process_next=cast(TaxonomyLayoutRuntimeProcessor, process_next_card_scope_layout),
            options=options,
        )
    finally:
        await runtime.redis.aclose()
        await runtime.engine.dispose()


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--wait", action="store_true")
    parser.add_argument("--timeout-seconds", type=float, default=900.0)
    parser.add_argument("--poll-interval-seconds", type=float, default=1.0)
    parser.add_argument("--json", action="store_true", dest="json_output")
    args = parser.parse_args(argv)
    if args.timeout_seconds < 0:
        parser.error("--timeout-seconds must be greater than or equal to 0.")
    if args.poll_interval_seconds < 0:
        parser.error("--poll-interval-seconds must be greater than or equal to 0.")
    return args


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    run = asyncio.run(
        _run_with_runtime(
            options=TaxonomyLayoutPrecomputeOptions(
                wait=args.wait,
                timeout_seconds=args.timeout_seconds,
                poll_interval_seconds=args.poll_interval_seconds,
            )
        )
    )
    print(format_run(run, as_json=args.json_output))
    return exit_code_for_run(run)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
