from __future__ import annotations

from pathlib import Path

from run_science_ingestion import (
    dedupe_page_records,
    load_science_query_batches,
)
from wiki_page_to_cards_types import PageRecord


def test_load_science_query_batches_reads_yaml(tmp_path: Path) -> None:
    config_path = tmp_path / "science-query-batches.yaml"
    config_path.write_text(
        """
batches:
  - name: physics-core
    query: physics force motion energy
    limit: 40
  - name: chemistry-core
    query: chemistry atom molecule reaction
    limit: 30
""".strip(),
        encoding="utf-8",
    )

    config = load_science_query_batches(config_path)

    assert [batch.name for batch in config.batches] == [
        "physics-core",
        "chemistry-core",
    ]
    assert config.batches[0].query == "physics force motion energy"
    assert config.batches[1].limit == 30


def test_dedupe_page_records_preserves_first_seen_order() -> None:
    pages = [
        PageRecord(page_id=1, url="u1", title="t1", clean_text="c1"),
        PageRecord(page_id=2, url="u2", title="t2", clean_text="c2"),
        PageRecord(page_id=1, url="u1b", title="t1b", clean_text="c1b"),
        PageRecord(page_id=3, url="u3", title="t3", clean_text="c3"),
    ]

    deduped = dedupe_page_records(pages)

    assert [page.page_id for page in deduped] == [1, 2, 3]
    assert deduped[0].title == "t1b"
