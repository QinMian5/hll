"""
Abstract: Contract tests for streaming Wikipedia page extraction and classification.
Out of scope: Artifact writing, run orchestration, and clean-text normalization.
"""

from __future__ import annotations

import bz2
from pathlib import Path

import pytest

from wiki_preprocess_classify import build_redirect_record, classify_page
from wiki_preprocess_types import PageExtractionResult, PageKind
from wiki_preprocess_xml import stream_pages


def _page_objects_from_split(sample_bz2_split: Path) -> dict[str, object]:
    return {
        page.title: page
        for page in stream_pages(sample_bz2_split, source_dump="enwiki-20260301")
    }


def test_stream_pages_reads_main_fields_from_bz2_split(sample_bz2_split: Path) -> None:
    pages = list(stream_pages(sample_bz2_split, source_dump="enwiki-20260301"))
    assert [page.title for page in pages] == [
        "Alan Turing",
        "USA",
        "Mercury (disambiguation)",
        "Talk:Alan Turing",
    ]
    assert pages[0].page_id == 100
    assert pages[0].revision_id == 1000
    assert pages[0].revision_timestamp == "2026-03-01T00:00:00Z"
    assert pages[1].redirect_target == "United States"


def test_classify_page_routes_redirect_and_disambiguation(sample_bz2_split: Path) -> None:
    pages = _page_objects_from_split(sample_bz2_split)
    assert classify_page(pages["Alan Turing"]).kind is PageKind.canonical_article
    assert classify_page(pages["USA"]).kind is PageKind.redirect_alias
    assert classify_page(pages["Mercury (disambiguation)"]).kind is PageKind.disambiguation
    assert classify_page(pages["Talk:Alan Turing"]).kind is PageKind.ignored


def test_redirect_source_url_comes_from_redirect_title(sample_bz2_split: Path) -> None:
    record = build_redirect_record(
        _page_objects_from_split(sample_bz2_split)["USA"],
        source_dump="enwiki-20260301",
    )
    assert record.source_url == "https://en.wikipedia.org/wiki/USA"


def test_stream_pages_can_skip_bad_pages_with_error_callback(tmp_path: Path) -> None:
    split_path = tmp_path / "pages-articles-multistream-00002.xml-00000.bz2"
    split_path.write_bytes(
        bz2.compress(
            b"""
<mediawiki>
  <page>
    <title>Good One</title>
    <ns>0</ns>
    <id>200</id>
    <revision>
      <id>2000</id>
      <timestamp>2026-03-01T00:10:00Z</timestamp>
      <text xml:space="preserve">Good page one.</text>
    </revision>
  </page>
  <page>
    <title>Broken Page</title>
    <ns>0</ns>
    <id>201</id>
  </page>
  <page>
    <title>Good Two</title>
    <ns>0</ns>
    <id>202</id>
    <revision>
      <id>2002</id>
      <timestamp>2026-03-01T00:12:00Z</timestamp>
      <text xml:space="preserve">Good page two.</text>
    </revision>
  </page>
</mediawiki>
"""
        )
    )

    failures: list[tuple[str, str | None]] = []
    pages = list(
        stream_pages(
            split_path,
            source_dump="enwiki-20260301",
            on_page_error=lambda error, context: failures.append(
                (type(error).__name__, context.get("title"))
            ),
        )
    )

    assert [page.title for page in pages] == ["Good One", "Good Two"]
    assert failures == [("ValueError", "Broken Page")]


def test_classify_page_keeps_literal_template_mentions_as_canonical() -> None:
    page = PageExtractionResult(
        page_id=300,
        title="Example Article",
        ns=0,
        revision_id=3000,
        revision_timestamp="2026-03-01T00:20:00Z",
        source_dump="enwiki-20260301",
        source_url="https://en.wikipedia.org/wiki/Example_Article",
        raw_text="This article documents the literal text {{disambiguation}} in a template manual.",
    )
    assert classify_page(page).kind is PageKind.canonical_article


def test_classify_page_detects_disambiguation_after_leading_comment() -> None:
    page = PageExtractionResult(
        page_id=301,
        title="Example Topic",
        ns=0,
        revision_id=3001,
        revision_timestamp="2026-03-01T00:21:00Z",
        source_dump="enwiki-20260301",
        source_url="https://en.wikipedia.org/wiki/Example_Topic",
        raw_text="<!--leading comment-->\n{{disambiguation}}",
    )
    assert classify_page(page).kind is PageKind.disambiguation


def test_build_redirect_record_rejects_source_dump_drift(sample_bz2_split: Path) -> None:
    with pytest.raises(ValueError, match="source_dump"):
        build_redirect_record(
            _page_objects_from_split(sample_bz2_split)["USA"],
            source_dump="other-dump",
        )
