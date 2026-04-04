"""
Abstract: Conservative classification helpers for Wikipedia page extraction results.
Out of scope: XML parsing, clean-text normalization, and run orchestration.
"""

from __future__ import annotations

import re
from dataclasses import replace

import mwparserfromhell
from mwparserfromhell.nodes import Comment, Template, Text, Wikilink

from wiki_preprocess_clean import _contains_wikicode_markup, has_readable_content
from wiki_preprocess_types import PageExtractionResult, PageKind, RedirectAliasRecord

_DISAMBIGUATION_TEMPLATE_NAMES = {
    "disambiguation",
    "disambig",
    "hndis",
    "geodis",
}
_NON_CONTENT_NAMESPACES = {"category", "file", "image", "media"}
_COMMENT_RE = re.compile(r"(?s)<!--.*?-->")
_TEXTUAL_REDIRECT_RE = re.compile(
    r"(?im)^\s*#redirect\s*:?\s*\[\[(?P<target>[^\[\]\n]+?)\]\]",
)
_DISAMBIGUATION_SIGNAL_RE = re.compile(
    r"(?is)\{\{\s*(?:disambiguation|disambig|hndis|geodis)\b"
)


def _strip_comments(text: str) -> str:
    return _COMMENT_RE.sub(" ", text)


def _extract_textual_redirect_target(page: PageExtractionResult) -> str | None:
    match = _TEXTUAL_REDIRECT_RE.search(_strip_comments(page.raw_text))
    if match is None:
        return None
    return match.group("target").strip()


def _is_non_content_wikilink(node: Wikilink) -> bool:
    title_text = str(node.title).strip()
    if title_text.startswith(":"):
        title_text = title_text[1:].lstrip()
    namespace = title_text.split(":", 1)[0].casefold()
    return namespace in _NON_CONTENT_NAMESPACES


def _is_disambiguation(page: PageExtractionResult) -> bool:
    lowered_title = page.title.casefold()
    if lowered_title.endswith("(disambiguation)"):
        return True
    comment_stripped = _strip_comments(page.raw_text)
    if _DISAMBIGUATION_SIGNAL_RE.search(comment_stripped) is None:
        return False
    parsed = mwparserfromhell.parse(comment_stripped)
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


def _is_effectively_empty(page: PageExtractionResult) -> bool:
    if not _contains_wikicode_markup(page.raw_text):
        return not any(character.isalnum() for character in page.raw_text)
    return not has_readable_content(page.raw_text)


def classify_page(page: PageExtractionResult) -> PageExtractionResult:
    if page.ns != 0:
        return replace(page, kind=PageKind.ignored)
    if page.redirect_target is not None:
        return replace(page, kind=PageKind.redirect_alias)
    textual_redirect_target = _extract_textual_redirect_target(page)
    if textual_redirect_target is not None:
        return replace(
            page,
            kind=PageKind.redirect_alias,
            redirect_target=textual_redirect_target,
        )
    if _is_disambiguation(page):
        return replace(page, kind=PageKind.disambiguation)
    if _is_effectively_empty(page):
        return replace(page, kind=PageKind.ignored)
    return replace(page, kind=PageKind.canonical_article)


def build_redirect_record(
    page: PageExtractionResult,
    *,
    source_dump: str,
) -> RedirectAliasRecord:
    classified_page = classify_page(page)
    if classified_page.kind is not PageKind.redirect_alias:
        raise ValueError("page must classify as a redirect alias")
    if classified_page.redirect_target is None:
        raise ValueError("redirect_target is required to build a redirect record")
    if source_dump != classified_page.source_dump:
        raise ValueError("source_dump must match the page source_dump")
    return RedirectAliasRecord(
        redirect_title=classified_page.title,
        canonical_title=classified_page.redirect_target,
        source_dump=classified_page.source_dump,
        source_url=classified_page.source_url,
    )
