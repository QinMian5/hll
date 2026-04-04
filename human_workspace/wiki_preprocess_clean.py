"""
Abstract: Structure-aware wikitext cleaning utilities for canonical Wikipedia text.
Out of scope: XML extraction, page classification, and artifact writing.
"""

from __future__ import annotations

import re

import mwparserfromhell

_NON_CONTENT_NAMESPACES = {"category", "file", "image", "media"}
_HEADING_RE = re.compile(r"^\s*(=+)\s*(.*?)\s*\1\s*$")
_LIST_RE = re.compile(r"^\s*([*#;:]+)\s*(.*?)\s*$")
_CONTROL_WORD_RE = re.compile(r"^\s*__\w+__\s*$")
_RESIDUE_RE = re.compile(r"(\{\{|\}\}|\[\[|\]\]|\{\||\|\}|<\s*/?\s*\w+[^>]*>)")


class CleaningError(ValueError):
    """Raised when wikitext cannot be reduced to readable prose."""


def _normalize_inline_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _is_non_content_wikilink(node: object) -> bool:
    title = getattr(node, "title", None)
    if title is None:
        return False
    title_text = str(title).strip()
    if title_text.startswith(":"):
        title_text = title_text[1:].lstrip()
    namespace = title_text.split(":", 1)[0].casefold()
    return namespace in _NON_CONTENT_NAMESPACES


def _remove_noise_nodes(code: mwparserfromhell.wikicode.Wikicode) -> None:
    for node in list(code.filter_comments(recursive=True)):
        code.remove(node)
    for node in list(code.filter_templates(recursive=True)):
        code.remove(node)
    for node in list(code.filter_tags(recursive=True)):
        code.replace(node, " ")
    for node in list(code.filter_wikilinks(recursive=True)):
        if _is_non_content_wikilink(node):
            code.remove(node)


def _clean_inline_fragment(fragment: str) -> str:
    code = mwparserfromhell.parse(fragment)
    _remove_noise_nodes(code)
    return _normalize_inline_text(code.strip_code(normalize=True, collapse=True))


def _append_block(lines: list[str], text: str, kind: str, last_kind: str | None) -> str:
    if lines and lines[-1] != "":
        if kind != "list" or last_kind != "list":
            lines.append("")
    lines.append(text.rstrip())
    return kind


def _normalize_output_lines(lines: list[str]) -> str:
    cleaned_lines: list[str] = []
    previous_blank = False
    for line in lines:
        stripped = line.rstrip()
        if not stripped:
            if cleaned_lines and not previous_blank:
                cleaned_lines.append("")
                previous_blank = True
            continue
        cleaned_lines.append(stripped)
        previous_blank = False
    while cleaned_lines and not cleaned_lines[0]:
        cleaned_lines.pop(0)
    while cleaned_lines and not cleaned_lines[-1]:
        cleaned_lines.pop()
    return "\n".join(cleaned_lines).strip()


def _contains_residue(text: str) -> bool:
    return bool(_RESIDUE_RE.search(text))


def clean_wikitext(wikitext: str) -> str:
    """Convert raw Wikipedia wikitext into readable plain text."""

    mwparserfromhell.parse(wikitext)

    output_lines: list[str] = []
    paragraph_lines: list[str] = []
    last_kind: str | None = None
    in_table = False

    def flush_paragraph() -> None:
        nonlocal last_kind
        if not paragraph_lines:
            return
        paragraph_text = " ".join(part.strip() for part in paragraph_lines if part.strip())
        paragraph_lines.clear()
        cleaned = _clean_inline_fragment(paragraph_text)
        if cleaned:
            last_kind = _append_block(output_lines, cleaned, "paragraph", last_kind)

    for raw_line in wikitext.splitlines():
        stripped = raw_line.strip()

        if in_table:
            if stripped.startswith("|}"):
                in_table = False
            continue

        if not stripped:
            flush_paragraph()
            continue

        if stripped.startswith("{|"):
            flush_paragraph()
            in_table = True
            continue

        if _CONTROL_WORD_RE.fullmatch(stripped):
            flush_paragraph()
            continue

        heading_match = _HEADING_RE.match(raw_line)
        if heading_match and 2 <= len(heading_match.group(1)) <= 6:
            flush_paragraph()
            heading_text = _clean_inline_fragment(heading_match.group(2))
            if heading_text:
                last_kind = _append_block(output_lines, heading_text, "heading", last_kind)
            continue

        list_match = _LIST_RE.match(raw_line)
        if list_match and stripped[:1] in {"*", "#", ";", ":"}:
            flush_paragraph()
            list_text = _clean_inline_fragment(list_match.group(2))
            if list_text:
                last_kind = _append_block(output_lines, f"- {list_text}", "list", last_kind)
            continue

        paragraph_lines.append(raw_line)

    flush_paragraph()
    cleaned = _normalize_output_lines(output_lines)

    if not cleaned or not any(character.isalnum() for character in cleaned):
        raise CleaningError("cleaned wikitext is empty or non-readable")
    if _contains_residue(cleaned):
        raise CleaningError("cleaned wikitext still contains wiki markup residue")

    return cleaned
