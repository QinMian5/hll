"""
Abstract: Top-level page-to-card orchestration for bounded concurrent page sessions.
Out of scope: Page discovery, topic filtering, and card-level checkpointing.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Sequence
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass

from knowledge_corpus.config import load_settings
from knowledge_corpus.db.session import SessionFactory, build_session_factory
from knowledge_corpus.wikipedia.service import mark_document_processed

from wiki_page_to_cards_cursor import PageAgentSettings, run_page_session
from wiki_page_to_cards_types import (
    PageRecord,
    PageResult,
    failed_page_result,
)


PageSessionRunner = Callable[[PageRecord], PageResult]
ProcessedMarker = Callable[..., None]
PageFinishedCallback = Callable[[PageRecord, PageResult], None]


@dataclass(slots=True)
class _ProcessedMarkerRuntime:
    mark_processed: ProcessedMarker
    close: Callable[[], None]


def build_external_target_ref(page_id: int) -> str:
    return f"cursor-page-agent:wikipedia:{page_id}"


async def _mark_processed_async(
    session_factory: SessionFactory,
    *,
    page_id: int,
    external_target_ref: str,
) -> None:
    async with session_factory() as session:
        async with session.begin():
            await mark_document_processed(
                session,
                page_id=page_id,
                external_target_ref=external_target_ref,
            )


def _build_default_processed_marker() -> _ProcessedMarkerRuntime:
    settings = load_settings()
    engine, session_factory = build_session_factory(settings)

    def mark_processed(*, page_id: int, external_target_ref: str) -> None:
        asyncio.run(
            _mark_processed_async(
                session_factory,
                page_id=page_id,
                external_target_ref=external_target_ref,
            )
        )

    def close() -> None:
        asyncio.run(engine.dispose())

    return _ProcessedMarkerRuntime(mark_processed=mark_processed, close=close)


def _default_run_page_session(page: PageRecord) -> PageResult:
    return run_page_session(page, settings=PageAgentSettings())


def _format_failure_reason(exc: Exception) -> str:
    message = str(exc).strip()
    if message:
        return message
    return exc.__class__.__name__


def run_pages(
    pages: Sequence[PageRecord],
    *,
    max_workers: int,
    run_page_session: PageSessionRunner | None = None,
    mark_processed: ProcessedMarker | None = None,
    on_page_finished: PageFinishedCallback | None = None,
) -> list[PageResult]:
    if max_workers < 1:
        raise ValueError("max_workers must be at least 1")

    page_runner = run_page_session or _default_run_page_session
    processed_runtime = (
        None if mark_processed is not None else _build_default_processed_marker()
    )
    processed_marker = (
        mark_processed if mark_processed is not None else processed_runtime.mark_processed
    )

    results: list[PageResult | None] = [None] * len(pages)
    try:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_index = {
                executor.submit(page_runner, page): index
                for index, page in enumerate(pages)
            }

            for future in as_completed(future_to_index):
                index = future_to_index[future]
                page = pages[index]
                try:
                    page_result = future.result()
                except Exception as exc:
                    page_result = failed_page_result(
                        page.page_id,
                        _format_failure_reason(exc),
                    )

                try:
                    processed_marker(
                        page_id=page.page_id,
                        external_target_ref=build_external_target_ref(page.page_id),
                    )
                except Exception as exc:
                    page_result = failed_page_result(
                        page.page_id,
                        _format_failure_reason(exc),
                    )

                results[index] = page_result
                if on_page_finished is not None:
                    on_page_finished(page, page_result)
    finally:
        if processed_runtime is not None:
            processed_runtime.close()

    return [result for result in results if result is not None]
