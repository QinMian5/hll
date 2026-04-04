"""
Abstract: Contract tests for structure-aware Wikipedia wikitext cleaning.
Out of scope: XML extraction, page classification, and artifact writing.
"""

from __future__ import annotations

import pytest

from wiki_preprocess_clean import CleaningError, clean_wikitext

RAW_WIKITEXT = """
Lead sentence.<ref>citation</ref>

== History ==
* First item
* Second item with [[Alan Turing|link text]]
{{Infobox scientist}}
[[Category:Computing]]
[[File:Example.jpg|thumb|caption]]
"""


def test_clean_text_keeps_headings_paragraphs_and_lists() -> None:
    cleaned = clean_wikitext(RAW_WIKITEXT)

    assert cleaned == (
        "Lead sentence.\n\n"
        "History\n\n"
        "- First item\n"
        "- Second item with link text"
    )


def test_clean_text_removes_templates_refs_categories_and_files() -> None:
    cleaned = clean_wikitext(RAW_WIKITEXT)

    assert "Infobox scientist" not in cleaned
    assert "citation" not in cleaned
    assert "Category:" not in cleaned
    assert "Example.jpg" not in cleaned


def test_clean_text_preserves_meaningful_external_link_anchors() -> None:
    cleaned = clean_wikitext("See [https://example.com Example site] for details.")

    assert cleaned == "See Example site for details."


def test_clean_text_removes_colon_prefixed_non_content_namespace_links() -> None:
    cleaned = clean_wikitext("[[:File:Example.jpg]] appears in the source.")

    assert cleaned == "appears in the source."


def test_clean_text_preserves_word_boundaries_when_tags_are_removed() -> None:
    cleaned = clean_wikitext("Alpha<br />Beta and Alpha<ref>note</ref>Beta.")

    assert cleaned == "Alpha Beta and Alpha Beta."


def test_clean_text_rejects_effectively_empty_output() -> None:
    with pytest.raises(CleaningError):
        clean_wikitext("{{disambiguation}}")


def test_clean_text_preserves_unicode_characters() -> None:
    cleaned = clean_wikitext("Café π 東京")

    assert "Café" in cleaned
    assert "π" in cleaned
    assert "東京" in cleaned
