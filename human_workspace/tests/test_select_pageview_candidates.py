"""
Abstract: Tests for one-shot Pageviews-based Wikipedia candidate selection.
Out of scope: Live Wikimedia API calls, Docker PostgreSQL access, and zstd shard streaming.
"""

from __future__ import annotations

from select_pageview_candidates import (
    AggregatedPage,
    ArticleRecord,
    aggregate_pageviews,
    build_candidate_rows,
    normalize_api_article_title,
    reject_reason_for_article_record,
    reject_reason_for_title,
)


def test_normalize_api_article_title_decodes_pageview_article_keys() -> None:
    assert normalize_api_article_title("Project_Hail_Mary_%28novel%29") == (
        "Project Hail Mary (novel)"
    )


def test_reject_reason_for_title_rejects_non_article_and_low_signal_titles() -> None:
    assert reject_reason_for_title("Main Page") == "main_page"
    assert reject_reason_for_title(".xxx") == "low_signal_title"
    assert reject_reason_for_title("Special:Search") == "namespace"
    assert reject_reason_for_title("List of highest-grossing films") == "list"
    assert reject_reason_for_title("Deaths in 2026") == "deaths"
    assert reject_reason_for_title("XXX (2002 film)") == "entertainment"
    assert reject_reason_for_title("XXX (film series)") == "entertainment"
    assert reject_reason_for_title("Quantum mechanics") is None


def test_reject_reason_for_article_record_rejects_obvious_low_knowledge_noise() -> None:
    assert (
        reject_reason_for_article_record(
            ArticleRecord(
                page_id=1,
                title="Celebrity",
                url="https://en.wikipedia.org/wiki/Celebrity",
                text_length=5000,
                lead_text="Celebrity is an American actor and singer.",
            )
        )
        == "lead_biography_noise"
    )
    assert (
        reject_reason_for_article_record(
            ArticleRecord(
                page_id=3,
                title="Rapper",
                url="https://en.wikipedia.org/wiki/Rapper",
                text_length=5000,
                lead_text="Rapper was an American rapper and songwriter.",
            )
        )
        == "lead_biography_noise"
    )
    assert (
        reject_reason_for_article_record(
            ArticleRecord(
                page_id=5,
                title="Athlete",
                url="https://en.wikipedia.org/wiki/Athlete",
                text_length=5000,
                lead_text="Athlete is an American professional baseball outfielder.",
            )
        )
        == "lead_biography_noise"
    )
    assert (
        reject_reason_for_article_record(
            ArticleRecord(
                page_id=4,
                title="Popular film",
                url="https://en.wikipedia.org/wiki/Popular_film",
                text_length=5000,
                lead_text="Popular film is a 2024 American superhero film.",
            )
        )
        == "lead_entertainment_noise"
    )
    assert (
        reject_reason_for_article_record(
            ArticleRecord(
                page_id=6,
                title="Adult site",
                url="https://en.wikipedia.org/wiki/Adult_site",
                text_length=5000,
                lead_text="Adult site is a pornographic video sharing website.",
            )
        )
        == "lead_adult_entertainment_noise"
    )
    assert (
        reject_reason_for_article_record(
            ArticleRecord(
                page_id=7,
                title="Small place",
                url="https://en.wikipedia.org/wiki/Small_place",
                text_length=2500,
                lead_text="Small place is an unincorporated community in Example County.",
            )
        )
        == "lead_low_signal_locality"
    )
    assert (
        reject_reason_for_article_record(
            ArticleRecord(
                page_id=2,
                title="Quantum mechanics",
                url="https://en.wikipedia.org/wiki/Quantum_mechanics",
                text_length=5000,
                lead_text="Quantum mechanics is a fundamental theory in physics.",
            )
        )
        is None
    )


def test_aggregate_pageviews_rewards_stable_monthly_popularity() -> None:
    month_payloads = {
        "2026-03": [
            {"article": "Stable_topic", "views": 1000, "rank": 5},
            {"article": "One_month_spike", "views": 5000, "rank": 1},
        ],
        "2026-04": [
            {"article": "Stable_topic", "views": 1000, "rank": 4},
        ],
    }

    pages = aggregate_pageviews(month_payloads, stable_month_bonus=3000)

    assert [page.title for page in pages] == ["Stable topic", "One month spike"]
    assert pages[0] == AggregatedPage(
        title="Stable topic",
        total_views=2000,
        months_seen=2,
        best_rank=4,
        score=8000,
    )


def test_build_candidate_rows_filters_and_orders_article_records() -> None:
    aggregates = [
        AggregatedPage(
            title="Quantum mechanics",
            total_views=5000,
            months_seen=2,
            best_rank=10,
            score=25000,
        ),
        AggregatedPage(
            title="Short article",
            total_views=100000,
            months_seen=1,
            best_rank=1,
            score=200000,
        ),
        AggregatedPage(
            title="Processed article",
            total_views=90000,
            months_seen=1,
            best_rank=2,
            score=190000,
        ),
        AggregatedPage(
            title="Mercury",
            total_views=80000,
            months_seen=1,
            best_rank=3,
            score=180000,
        ),
    ]
    article_records = {
        "Quantum mechanics": ArticleRecord(
            page_id=1,
            title="Quantum mechanics",
            url="https://en.wikipedia.org/wiki/Quantum_mechanics",
            text_length=5000,
        ),
        "Short article": ArticleRecord(
            page_id=2,
            title="Short article",
            url="https://en.wikipedia.org/wiki/Short_article",
            text_length=200,
        ),
        "Processed article": ArticleRecord(
            page_id=3,
            title="Processed article",
            url="https://en.wikipedia.org/wiki/Processed_article",
            text_length=5000,
        ),
        "Mercury": ArticleRecord(
            page_id=4,
            title="Mercury",
            url="https://en.wikipedia.org/wiki/Mercury",
            text_length=5000,
        ),
    }

    rows, summary = build_candidate_rows(
        aggregates,
        article_records=article_records,
        disambiguation_titles={"Mercury"},
        processed_page_ids={3},
        min_text_length=1500,
        max_pages=10,
    )

    assert [row.title for row in rows] == ["Quantum mechanics"]
    assert summary["selected"] == 1
    assert summary["rejected_short_text"] == 1
    assert summary["rejected_processed"] == 1
    assert summary["rejected_disambiguation"] == 1
