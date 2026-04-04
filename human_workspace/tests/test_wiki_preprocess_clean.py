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


def test_clean_text_uses_fast_path_for_plain_text(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _raise_unexpected_parse(_: str) -> object:
        raise AssertionError("plain text cleaning should not parse wikicode")

    monkeypatch.setattr("wiki_preprocess_clean.mwparserfromhell.parse", _raise_unexpected_parse)

    assert clean_wikitext("A plain sentence without wikicode.") == (
        "A plain sentence without wikicode."
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


def test_clean_text_removes_multiline_infobox_before_inline_parsing() -> None:
    cleaned = clean_wikitext(
        """
{{Infobox settlement
| name = Matsari
| subdivision_name = {{flag|Nepal}}
}}
Lead sentence.
""".strip(),
    )

    assert cleaned == "Lead sentence."


def test_clean_text_handles_multiline_templates_with_nested_templates() -> None:
    cleaned = clean_wikitext(
        """
{{Multiple issues|
{{BLP sources|date=July 2010}}
{{Expand French|date=December 2008|topic=gov|Bernard Reynès}}
}}

Bernard Reynès is a French politician.
""".strip(),
    )

    assert cleaned == "Bernard Reynès is a French politician."


def test_clean_text_removes_multiline_reference_blocks_with_inline_prefix() -> None:
    cleaned = clean_wikitext(
        """
Lead sentence<ref>
{{cite web|title=Source}}
</ref>

Follow-up sentence.
""".strip(),
    )

    assert cleaned == "Lead sentence\n\nFollow-up sentence."


def test_clean_text_ignores_literal_ref_markup_inside_html_comments() -> None:
    cleaned = clean_wikitext(
        """
{{Infobox settlement
| population_footnotes = <!-- for references: use <ref> tags -->
| coordinates = {{coord|43|19|45|N|5|38|36|W|display=inline,title}}
}}
'''Tuilla'''<ref>{{cite web|title=Source}}</ref> is a village in Asturias.
""".strip(),
    )

    assert cleaned == "Tuilla is a village in Asturias."


def test_clean_text_skips_template_only_list_items() -> None:
    cleaned = clean_wikitext(
        """
== Further reading ==
* {{cite book
| title = Example Book
}}
* Real item
""".strip(),
    )

    assert cleaned == "Further reading\n\n- Real item"


def test_clean_text_does_not_overmatch_self_closing_named_refs() -> None:
    cleaned = clean_wikitext(
        """
Lead sentence.<ref name=sr/> More text.

Another fact.<ref name=sr>{{cite web|title=Source}}</ref>
""".strip(),
    )

    assert cleaned == "Lead sentence. More text.\n\nAnother fact."


def test_clean_text_preserves_bolded_subject_terms() -> None:
    cleaned = clean_wikitext("'''Thiksey''' is a village.")

    assert cleaned == "Thiksey is a village."


def test_clean_text_preserves_bolded_inline_nicknames() -> None:
    cleaned = clean_wikitext("He was known as the '''Forces of Evil'''.")

    assert cleaned == "He was known as the Forces of Evil."


def test_clean_text_removes_timeline_blocks() -> None:
    cleaned = clean_wikitext(
        """
Lead sentence.

<timeline>
ImageSize = width:500 height:65
</timeline>

Follow-up sentence.
""".strip(),
    )

    assert cleaned == "Lead sentence.\n\nFollow-up sentence."


def test_clean_text_removes_onlyinclude_wrapped_template_blocks() -> None:
    cleaned = clean_wikitext(
        """
Intro paragraph.

<onlyinclude>{{Series overview|color1=#000000}}</onlyinclude>

After paragraph.
""".strip(),
    )

    assert cleaned == "Intro paragraph.\n\nAfter paragraph."


def test_clean_text_removes_empty_references_blocks() -> None:
    cleaned = clean_wikitext(
        """
References

<references>
</references>

External links
""".strip(),
    )

    assert cleaned == "References\n\nExternal links"


def test_clean_text_removes_div_wrapped_timeline_sections() -> None:
    cleaned = clean_wikitext(
        """
Ranking leaders

<div style=text-align:center;float:right;clear:right;margin-left:1em>'''Timeline of leaders'''<br />
<timeline>
ImageSize = width:130 height:500
</timeline>
</div>

After paragraph.
""".strip(),
    )

    assert cleaned == "Ranking leaders\n\nAfter paragraph."


def test_clean_text_removes_gallery_blocks_attached_to_table_closers() -> None:
    cleaned = clean_wikitext(
        """
Fleet includes

|}<gallery mode="packed" heights="100">
File:One.jpg|One
</gallery>

After paragraph.
""".strip(),
    )

    assert cleaned == "Fleet includes\n\nAfter paragraph."


def test_clean_text_removes_multiline_templates_with_inline_prefix() -> None:
    cleaned = clean_wikitext(
        """
Votes were counted. {{Election results

}}

Aftermath
""".strip(),
    )

    assert cleaned == "Votes were counted.\n\nAftermath"


def test_clean_text_removes_inline_refn_templates_without_eating_neighbors() -> None:
    cleaned = clean_wikitext(
        """
The dynasty ruled Afghanistan{{refn|group=note|A supporting note.}} and Kashmir.
""".strip(),
    )

    assert cleaned == "The dynasty ruled Afghanistan and Kashmir."


def test_clean_text_removes_multiline_file_links_with_captions() -> None:
    cleaned = clean_wikitext(
        """
Overview paragraph.

[[File:Map.svg|thumb|Caption text:
* detail line
]]

After paragraph.
""".strip(),
    )

    assert cleaned == "Overview paragraph.\n\nAfter paragraph."


def test_clean_text_removes_file_links_with_nested_wikilinks_in_captions() -> None:
    cleaned = clean_wikitext(
        """
Overview paragraph.

[[File:Monument.jpg|thumb|A monument near [[Ministry of Defence]] in London.]]

After paragraph.
""".strip(),
    )

    assert cleaned == "Overview paragraph.\n\nAfter paragraph."


def test_clean_text_preserves_blockquote_contents_while_removing_tags() -> None:
    cleaned = clean_wikitext(
        """
Intro paragraph.

<blockquote>
Quoted text here.
</blockquote>

After paragraph.
""".strip(),
    )

    assert cleaned == "Intro paragraph.\n\nQuoted text here.\n\nAfter paragraph."


def test_clean_text_drops_math_blocks_without_failing_page_cleaning() -> None:
    cleaned = clean_wikitext(
        """
Equation

<math>
a^2 + b^2 = c^2
</math>

After paragraph.
""".strip(),
    )

    assert cleaned == "Equation\n\nAfter paragraph."


def test_clean_text_removes_stray_wikilink_brackets_after_cleaning() -> None:
    cleaned = clean_wikitext("Her show airs on [[Rouge FM My Heart )).")

    assert cleaned == "Her show airs on Rouge FM My Heart ))."


def test_clean_text_unwraps_angle_bracketed_urls_after_cleaning() -> None:
    cleaned = clean_wikitext("Reference <https://example.com/report.pdf>")

    assert cleaned == "Reference https://example.com/report.pdf"


def test_clean_text_treats_list_items_that_start_tables_as_table_blocks() -> None:
    cleaned = clean_wikitext(
        """
Season to season

* {| class="wikitable"
|-
| Row content
|}

After paragraph.
""".strip(),
    )

    assert cleaned == "Season to season\n\nAfter paragraph."


def test_clean_text_removes_formula_style_double_brace_residue() -> None:
    cleaned = clean_wikitext("Formula text \\end{align}} after.")

    assert cleaned == "Formula text \\end{align} after."


def test_clean_text_skips_orphan_table_control_lines() -> None:
    cleaned = clean_wikitext(
        """
Results

|-
| colspan=2 | Example
|}

Afterward.
""".strip(),
    )

    assert cleaned == "Results\n\nAfterward."


def test_clean_text_preserves_unicode_characters() -> None:
    cleaned = clean_wikitext("Café π 東京")

    assert "Café" in cleaned
    assert "π" in cleaned
    assert "東京" in cleaned
