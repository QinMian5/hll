from __future__ import annotations

from wiki_page_to_cards_orchestrator import run_pages
from wiki_page_to_cards_types import (
    PageRecord,
    completed_page_result,
    failed_page_result,
)


def test_run_pages_marks_every_finished_page() -> None:
    pages = [
        PageRecord(page_id=1, url="u1", title="t1", clean_text="c1"),
        PageRecord(page_id=2, url="u2", title="t2", clean_text="c2"),
    ]
    seen_marks: list[tuple[int, str]] = []

    def fake_runner(page: PageRecord):
        if page.page_id == 1:
            return completed_page_result(page.page_id)
        return failed_page_result(page.page_id, "rejected by page agent")

    def fake_mark_processed(*, page_id: int, external_target_ref: str) -> None:
        seen_marks.append((page_id, external_target_ref))

    results = run_pages(
        pages,
        max_workers=2,
        run_page_session=fake_runner,
        mark_processed=fake_mark_processed,
    )

    assert [result.completed for result in results] == [True, False]
    assert seen_marks == [
        (1, "cursor-page-agent:wikipedia:1"),
        (2, "cursor-page-agent:wikipedia:2"),
    ]


def test_run_pages_keeps_other_pages_running_when_one_fails() -> None:
    pages = [
        PageRecord(page_id=1, url="u1", title="t1", clean_text="c1"),
        PageRecord(page_id=2, url="u2", title="t2", clean_text="c2"),
    ]

    def fake_runner(page: PageRecord):
        if page.page_id == 1:
            raise RuntimeError("cursor failed")
        return completed_page_result(2)

    results = run_pages(
        pages,
        max_workers=2,
        run_page_session=fake_runner,
        mark_processed=lambda **kwargs: None,
    )

    assert {result.page_id: result.completed for result in results} == {
        1: False,
        2: True,
    }
    assert {result.page_id: result.reason for result in results} == {
        1: "cursor failed",
        2: None,
    }


def test_run_pages_returns_failure_reason_when_processed_mark_fails() -> None:
    pages = [
        PageRecord(page_id=1, url="u1", title="t1", clean_text="c1"),
    ]

    def fake_runner(page: PageRecord):
        return completed_page_result(page.page_id)

    def fake_mark_processed(*, page_id: int, external_target_ref: str) -> None:
        raise RuntimeError("processed mark failed")

    results = run_pages(
        pages,
        max_workers=1,
        run_page_session=fake_runner,
        mark_processed=fake_mark_processed,
    )

    assert results == [failed_page_result(1, "processed mark failed")]


def test_run_pages_emits_page_finished_callback() -> None:
    pages = [
        PageRecord(page_id=1, url="u1", title="t1", clean_text="c1"),
        PageRecord(page_id=2, url="u2", title="t2", clean_text="c2"),
    ]
    seen_finished: list[tuple[int, bool]] = []

    def fake_runner(page: PageRecord):
        if page.page_id == 1:
            return completed_page_result(page.page_id)
        return failed_page_result(page.page_id, "rejected by page agent")

    def on_page_finished(page: PageRecord, result) -> None:
        seen_finished.append((page.page_id, result.completed))

    run_pages(
        pages,
        max_workers=2,
        run_page_session=fake_runner,
        mark_processed=lambda **kwargs: None,
        on_page_finished=on_page_finished,
    )

    assert sorted(seen_finished) == [(1, True), (2, False)]
