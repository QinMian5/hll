"""
Abstract: Conservative classification helpers for Wikipedia page extraction results.
Out of scope: XML parsing, clean-text normalization, and run orchestration.
"""

from __future__ import annotations

from dataclasses import replace

import mwparserfromhell
from mwparserfromhell.nodes import Comment, Template, Text

from wiki_preprocess_types import PageExtractionResult, PageKind, RedirectAliasRecord

_DISAMBIGUATION_TEMPLATE_NAMES = {
    "disambiguation",
    "disambig",
    "hndis",
    "geodis",
}


def _is_disambiguation(page: PageExtractionResult) -> bool:
    lowered_title = page.title.casefold()
    if lowered_title.endswith("(disambiguation)"):
        return True
    parsed = mwparserfromhell.parse(page.raw_text)
    for node in parsed.nodes:
        if isinstance(node, Comment):
            continue
        if isinstance(node, Text):
            if not str(node.value).strip():
                continue
            return False
        if isinstance(node, Template):
            template_name = str(node.name).strip().casefold()
            if template_name in _DISAMBIGUATION_TEMPLATE_NAMES:
                return True
            continue
        return False
    return False


def classify_page(page: PageExtractionResult) -> PageExtractionResult:
    if page.ns != 0:
        return replace(page, kind=PageKind.ignored)
    if page.redirect_target is not None:
        return replace(page, kind=PageKind.redirect_alias)
    if _is_disambiguation(page):
        return replace(page, kind=PageKind.disambiguation)
    return replace(page, kind=PageKind.canonical_article)


def build_redirect_record(
    page: PageExtractionResult,
    *,
    source_dump: str,
) -> RedirectAliasRecord:
    if page.redirect_target is None:
        raise ValueError("redirect_target is required to build a redirect record")
    classified_page = classify_page(page)
    if classified_page.kind is not PageKind.redirect_alias:
        raise ValueError("page must classify as a redirect alias")
    if source_dump != classified_page.source_dump:
        raise ValueError("source_dump must match the page source_dump")
    return RedirectAliasRecord(
        redirect_title=classified_page.title,
        canonical_title=classified_page.redirect_target,
        source_dump=classified_page.source_dump,
        source_url=classified_page.source_url,
    )
