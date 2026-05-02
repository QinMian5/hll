"""
Abstract: Tests for Pageviews candidate submission into source-pipeline intake.
Out of scope: Live Docker PostgreSQL access, orchestrator polling, and job queue execution.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from submit_pageview_candidates_to_source_pipeline import (
    CorpusDocument,
    MissingCorpusDocumentsError,
    PageviewCandidate,
    build_source_unit,
    external_target_ref_for_page_id,
    load_pageview_candidates,
    plan_submission,
    source_ref_for_page_id,
)


def test_load_pageview_candidates_reads_ranked_jsonl(tmp_path: Path) -> None:
    path = tmp_path / "selected.jsonl"
    path.write_text(
        json.dumps(
            {
                "selection_rank": 1,
                "page_id": 72417803,
                "title": "ChatGPT",
                "url": "https://en.wikipedia.org/wiki/ChatGPT",
                "total_views": 63583861,
                "months_seen": 24,
                "best_rank": 5,
                "score": 65983861,
                "text_length": 34455,
            }
        )
        + "\n",
        encoding="utf-8",
    )

    candidates = load_pageview_candidates(path)

    assert candidates == [
        PageviewCandidate(
            selection_rank=1,
            page_id=72417803,
            title="ChatGPT",
            url="https://en.wikipedia.org/wiki/ChatGPT",
            total_views=63583861,
            months_seen=24,
            best_rank=5,
            score=65983861,
            text_length=34455,
        )
    ]


def test_build_source_unit_preserves_pageview_selection_metadata() -> None:
    candidate = PageviewCandidate(
        selection_rank=2,
        page_id=44534,
        title="1989 Tiananmen Square protests and massacre",
        url="https://en.wikipedia.org/wiki/1989_Tiananmen_Square_protests_and_massacre",
        total_views=63685983,
        months_seen=14,
        best_rank=3,
        score=65085983,
        text_length=98736,
    )
    document = CorpusDocument(
        page_id=44534,
        title="1989 Tiananmen Square protests and massacre",
        url="https://en.wikipedia.org/wiki/1989_Tiananmen_Square_protests_and_massacre",
        clean_text="The 1989 Tiananmen Square protests were student-led demonstrations.",
    )

    unit = build_source_unit(candidate, document, selection_name="pageviews-top-2026-04")

    assert unit == {
        "source_kind": "wikipedia",
        "source_ref": "wikipedia:44534",
        "title": "1989 Tiananmen Square protests and massacre",
        "content": "The 1989 Tiananmen Square protests were student-led demonstrations.",
        "metadata": {
            "page_id": 44534,
            "url": "https://en.wikipedia.org/wiki/1989_Tiananmen_Square_protests_and_massacre",
            "selection_batch": "pageviews-top-2026-04",
            "selection_rank": 2,
            "pageview_total_views": 63685983,
            "pageview_months_seen": 14,
            "pageview_best_rank": 3,
            "pageview_score": 65085983,
            "selected_title": "1989 Tiananmen Square protests and massacre",
            "selected_url": "https://en.wikipedia.org/wiki/1989_Tiananmen_Square_protests_and_massacre",
            "selected_text_length": 98736,
        },
    }


def test_plan_submission_skips_existing_refs_and_marks_submitted_pages_processed() -> None:
    candidates = [
        PageviewCandidate(
            selection_rank=1,
            page_id=1,
            title="New page",
            url="https://en.wikipedia.org/wiki/New_page",
            total_views=100,
            months_seen=2,
            best_rank=10,
            score=200,
            text_length=5000,
        ),
        PageviewCandidate(
            selection_rank=2,
            page_id=2,
            title="Existing source unit",
            url="https://en.wikipedia.org/wiki/Existing_source_unit",
            total_views=90,
            months_seen=1,
            best_rank=20,
            score=190,
            text_length=5000,
        ),
        PageviewCandidate(
            selection_rank=3,
            page_id=3,
            title="Already processed",
            url="https://en.wikipedia.org/wiki/Already_processed",
            total_views=80,
            months_seen=1,
            best_rank=30,
            score=180,
            text_length=5000,
        ),
    ]
    documents = {
        1: CorpusDocument(
            page_id=1,
            title="New page",
            url="https://en.wikipedia.org/wiki/New_page",
            clean_text="New page content.",
        ),
        2: CorpusDocument(
            page_id=2,
            title="Existing source unit",
            url="https://en.wikipedia.org/wiki/Existing_source_unit",
            clean_text="Existing source content.",
        ),
        3: CorpusDocument(
            page_id=3,
            title="Already processed",
            url="https://en.wikipedia.org/wiki/Already_processed",
            clean_text="Already processed content.",
        ),
    }

    plan = plan_submission(
        candidates,
        documents=documents,
        existing_source_refs={source_ref_for_page_id(2)},
        processed_page_ids={3},
        selection_name="pageviews-top-2026-04",
    )

    assert [unit["source_ref"] for unit in plan.units_to_insert] == ["wikipedia:1"]
    assert plan.page_ids_to_mark_processed == {1, 2}
    assert plan.skipped_existing_source_refs == {source_ref_for_page_id(2)}
    assert plan.skipped_processed_page_ids == {3}


def test_plan_submission_requires_selected_pages_to_exist_in_corpus() -> None:
    candidate = PageviewCandidate(
        selection_rank=1,
        page_id=99,
        title="Missing page",
        url="https://en.wikipedia.org/wiki/Missing_page",
        total_views=100,
        months_seen=2,
        best_rank=10,
        score=200,
        text_length=5000,
    )

    with pytest.raises(MissingCorpusDocumentsError, match="99"):
        plan_submission(
            [candidate],
            documents={},
            existing_source_refs=set(),
            processed_page_ids=set(),
            selection_name="pageviews-top-2026-04",
        )


def test_source_and_processed_refs_are_stable() -> None:
    assert source_ref_for_page_id(42) == "wikipedia:42"
    assert external_target_ref_for_page_id(42) == "source-pipeline:wikipedia:42"
