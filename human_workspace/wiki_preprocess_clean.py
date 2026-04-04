"""
Abstract: Structure-aware wikitext cleaning utilities for canonical Wikipedia text.
Out of scope: XML extraction, page classification, and artifact writing.
"""

from __future__ import annotations

import re

import mwparserfromhell

_NON_CONTENT_NAMESPACES = {"category", "file", "image", "media"}
_SPACE_ONLY_TAGS = {"br"}
_BLOCK_TAG_NAMES = ("div", "gallery", "includeonly", "noinclude", "onlyinclude", "references", "timeline")
_HEADING_RE = re.compile(r"^\s*(=+)\s*(.*?)\s*\1\s*$")
_LIST_RE = re.compile(r"^\s*([*#;:]+)\s*(.*?)\s*$")
_CONTROL_WORD_RE = re.compile(r"^\s*__\w+__\s*$")
_RESIDUE_RE = re.compile(r"(\{\{|\}\}|\[\[|\]\]|\{\||\|\}|<\s*/?\s*\w+[^>]*>)")
_ANGLE_URL_RE = re.compile(r"<\s*(https?://[^>\s]+)\s*>")
_FINAL_TAG_RE = re.compile(r"</?[\w:-]+[^>\n]*>")
_COMMENT_RE = re.compile(r"(?s)<!--.*?-->")
_REF_BLOCK_RE = re.compile(r"(?is)<ref\b[^>]*?>.*?</ref\s*>")
_SELF_CLOSING_REF_RE = re.compile(r"(?is)<ref\b[^>]*/\s*>")
_BLOCK_TAG_RE = re.compile(
    rf"(?is)<(?P<tag>{'|'.join(_BLOCK_TAG_NAMES)})\b[^>]*?>.*?</(?P=tag)\s*>",
)
_SELF_CLOSING_BLOCK_TAG_RE = re.compile(
    rf"(?is)<(?:{'|'.join(_BLOCK_TAG_NAMES)})\b[^>]*/\s*>",
)
_NON_CONTENT_LINK_RE = re.compile(
    r"(?is)\[\[\s*:?\s*(?:category|file|image|media)\s*:[^\]]*\]\]"
)
_APOSTROPHE_MARKUP_RE = re.compile(r"'{2,5}")


class CleaningError(ValueError):
    """Raised when wikitext cannot be reduced to readable prose."""


def _normalize_inline_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _contains_wikicode_markup(text: str) -> bool:
    return any(
        token in text
        for token in ("[[", "{{", "]]", "}}", "<", ">", "''", "[http", "__")
    )


def _is_plain_text_document(text: str) -> bool:
    if _contains_wikicode_markup(text):
        return False
    for raw_line in text.splitlines():
        stripped = raw_line.strip()
        if not stripped:
            continue
        if _HEADING_RE.match(raw_line):
            return False
        if _LIST_RE.match(raw_line) and stripped[:1] in {"*", "#", ";", ":"}:
            return False
        if stripped.startswith("{|") or stripped.startswith("|}"):
            return False
        if _is_table_control_line(stripped):
            return False
        if _CONTROL_WORD_RE.fullmatch(stripped):
            return False
    return True


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
    for node in list(code.filter_comments(recursive=False)):
        code.remove(node)
    for node in list(code.filter_templates(recursive=False)):
        code.remove(node)
    for node in list(code.filter_tags(recursive=False)):
        if getattr(node, "wiki_markup", None) is not None:
            continue
        tag_name = str(getattr(node, "tag", "")).strip().casefold()
        if tag_name in _SPACE_ONLY_TAGS:
            code.replace(node, " ")
    for node in list(code.filter_wikilinks(recursive=False)):
        if _is_non_content_wikilink(node):
            code.remove(node)


def _clean_inline_fragment(fragment: str) -> str:
    if not _contains_wikicode_markup(fragment):
        return _normalize_inline_text(fragment)
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


def _finalize_cleaned_text(text: str) -> str:
    text = _ANGLE_URL_RE.sub(r" \1 ", text)
    text = _FINAL_TAG_RE.sub(" ", text)
    text = text.replace("{{", "{").replace("}}", "}")
    text = text.replace("[[", "").replace("]]", "")
    text = text.replace("<", " ").replace(">", " ")

    normalized_lines: list[str] = []
    for line in text.splitlines():
        if not line.strip():
            normalized_lines.append("")
            continue
        normalized_lines.append(_normalize_inline_text(line))
    return _normalize_output_lines(normalized_lines)


def _template_balance_delta(text: str) -> int:
    return text.count("{{") - text.count("}}")


def _strip_comments(wikitext: str) -> str:
    return _COMMENT_RE.sub(" ", wikitext)


def _strip_reference_blocks(wikitext: str) -> str:
    without_self_closing_refs = _SELF_CLOSING_REF_RE.sub(" ", wikitext)
    return _REF_BLOCK_RE.sub(" ", without_self_closing_refs)


def _strip_template_blocks(wikitext: str) -> str:
    output: list[str] = []
    depth = 0
    index = 0

    while index < len(wikitext):
        token = wikitext[index : index + 2]
        if depth == 0 and token == "{{":
            depth = 1
            output.append(" ")
            index += 2
            continue
        if depth > 0:
            if token == "{{":
                depth += 1
                index += 2
                continue
            if token == "}}":
                depth = max(0, depth - 1)
                index += 2
                if depth == 0:
                    output.append(" ")
                continue
            if wikitext[index] == "\n":
                output.append("\n")
            index += 1
            continue
        output.append(wikitext[index])
        index += 1

    return "".join(output)


def _starts_file_link(wikitext: str, index: int) -> bool:
    if wikitext[index : index + 2] != "[[":
        return False
    cursor = index + 2
    while cursor < len(wikitext) and wikitext[cursor].isspace():
        cursor += 1
    return (
        wikitext[cursor : cursor + 5].casefold() == "file:"
        or wikitext[cursor : cursor + 6].casefold() == "image:"
    )


def _strip_file_links(wikitext: str) -> str:
    output: list[str] = []
    depth = 0
    index = 0

    while index < len(wikitext):
        token = wikitext[index : index + 2]
        if depth == 0 and _starts_file_link(wikitext, index):
            depth = 1
            output.append(" ")
            index += 2
            continue
        if depth > 0:
            if token == "[[":
                depth += 1
                index += 2
                continue
            if token == "]]":
                depth = max(0, depth - 1)
                index += 2
                if depth == 0:
                    output.append(" ")
                continue
            if wikitext[index] == "\n":
                output.append("\n")
            index += 1
            continue
        output.append(wikitext[index])
        index += 1

    return "".join(output)


def _strip_named_block_tags(wikitext: str) -> str:
    without_self_closing_blocks = _SELF_CLOSING_BLOCK_TAG_RE.sub(" ", wikitext)
    return _BLOCK_TAG_RE.sub(" ", without_self_closing_blocks)


def strip_for_content_probe(wikitext: str) -> str:
    """Remove obvious markup noise cheaply for content-presence checks."""

    stripped = _strip_comments(wikitext)
    stripped = _strip_template_blocks(stripped)
    stripped = _strip_named_block_tags(stripped)
    stripped = _strip_file_links(stripped)
    stripped = _NON_CONTENT_LINK_RE.sub(" ", stripped)
    stripped = _FINAL_TAG_RE.sub(" ", stripped)
    stripped = _APOSTROPHE_MARKUP_RE.sub("", stripped)
    stripped = stripped.replace("[[", " ").replace("]]", " ")
    stripped = stripped.replace("{|", " ").replace("|}", " ")
    stripped = stripped.replace("|-", " ")
    return stripped


def has_readable_content(wikitext: str) -> bool:
    probe = strip_for_content_probe(wikitext)
    return any(character.isalnum() for character in probe)


def _is_table_control_line(stripped: str) -> bool:
    if not stripped:
        return False
    if stripped.startswith("|"):
        return True
    if not stripped.startswith("!"):
        return False
    return len(stripped) == 1 or stripped[1] in {" ", "!", "|"}


def clean_wikitext(wikitext: str) -> str:
    """Convert raw Wikipedia wikitext into readable plain text."""

    if _is_plain_text_document(wikitext):
        plain_lines = [
            _normalize_inline_text(line)
            for line in wikitext.splitlines()
            if _normalize_inline_text(line)
        ]
        cleaned_plain = _normalize_output_lines(plain_lines)
        if not cleaned_plain or not any(character.isalnum() for character in cleaned_plain):
            raise CleaningError("cleaned wikitext is empty or non-readable")
        return cleaned_plain

    wikitext = _strip_comments(wikitext)
    wikitext = _strip_reference_blocks(wikitext)
    wikitext = _strip_template_blocks(wikitext)
    wikitext = _strip_named_block_tags(wikitext)
    wikitext = _strip_file_links(wikitext)

    output_lines: list[str] = []
    paragraph_lines: list[str] = []
    last_kind: str | None = None
    in_table = False
    template_depth = 0

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

        if template_depth > 0:
            template_depth = max(0, template_depth + _template_balance_delta(raw_line))
            continue

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

        if _is_table_control_line(stripped):
            flush_paragraph()
            continue

        template_delta = _template_balance_delta(raw_line)
        if stripped.startswith("{{"):
            flush_paragraph()
            if template_delta >= 0:
                template_depth = max(template_delta, 0)
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
            list_body = list_match.group(2).lstrip()
            if list_body.startswith("{|"):
                flush_paragraph()
                in_table = True
                continue
            body_template_delta = _template_balance_delta(list_body)
            if list_body.startswith("{{") and body_template_delta > 0:
                flush_paragraph()
                template_depth = body_template_delta
                continue
            flush_paragraph()
            list_text = _clean_inline_fragment(list_match.group(2))
            if list_text:
                last_kind = _append_block(output_lines, f"- {list_text}", "list", last_kind)
            continue

        paragraph_lines.append(raw_line)

    flush_paragraph()
    cleaned = _finalize_cleaned_text(_normalize_output_lines(output_lines))

    if not cleaned or not any(character.isalnum() for character in cleaned):
        raise CleaningError("cleaned wikitext is empty or non-readable")
    if _contains_residue(cleaned):
        raise CleaningError("cleaned wikitext still contains wiki markup residue")

    return cleaned
