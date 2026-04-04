"""
Abstract: Streaming XML extraction for Wikipedia multistream split files.
Out of scope: Page classification, text cleaning, and artifact persistence.
"""

from __future__ import annotations

import bz2
from pathlib import Path
from typing import Callable, Iterator
from urllib.parse import quote

from lxml import etree

from wiki_preprocess_types import PageExtractionResult


def _local_name(tag: str) -> str:
    if "}" in tag:
        return tag.rsplit("}", 1)[1]
    return tag


def _first_child(element: etree._Element, child_name: str) -> etree._Element | None:
    for child in element:
        if _local_name(child.tag) == child_name:
            return child
    return None


def _first_child_text(element: etree._Element, child_name: str) -> str | None:
    child = _first_child(element, child_name)
    if child is None or child.text is None:
        return None
    return child.text


def _canonical_page_url(title: str) -> str:
    normalized_title = title.replace(" ", "_")
    return f"https://en.wikipedia.org/wiki/{quote(normalized_title, safe='()')}"


def stream_pages(
    split_path: str | Path,
    *,
    source_dump: str,
    on_page_error: Callable[[Exception, dict[str, object]], None] | None = None,
) -> Iterator[PageExtractionResult]:
    with bz2.open(split_path, "rb") as compressed_stream:
        context = etree.iterparse(compressed_stream, events=("end",))
        for _, element in context:
            if _local_name(element.tag) != "page":
                continue
            title = _first_child_text(element, "title")
            page_id_text = _first_child_text(element, "id")
            ns_text = _first_child_text(element, "ns")
            try:
                revision = _first_child(element, "revision")
                text = ""
                revision_id = 0
                revision_timestamp = ""
                if revision is not None:
                    text = _first_child_text(revision, "text") or ""
                    revision_id = int(_first_child_text(revision, "id") or "0")
                    revision_timestamp = _first_child_text(revision, "timestamp") or ""
                redirect = _first_child(element, "redirect")
                redirect_target = None
                if redirect is not None:
                    redirect_target = redirect.get("title")
                yield PageExtractionResult(
                    page_id=int(page_id_text or "0"),
                    title=title or "",
                    ns=int(ns_text or "0"),
                    revision_id=revision_id,
                    revision_timestamp=revision_timestamp,
                    source_dump=source_dump,
                    source_url=_canonical_page_url(title or ""),
                    raw_text=text,
                    redirect_target=redirect_target,
                )
            except Exception as error:
                if on_page_error is None:
                    raise
                on_page_error(
                    error,
                    {
                        "title": title,
                        "page_id": page_id_text,
                        "ns": ns_text,
                    },
                )
            element.clear()
            while element.getprevious() is not None:
                del element.getparent()[0]
