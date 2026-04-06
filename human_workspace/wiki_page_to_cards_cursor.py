"""
Abstract: One-page Cursor session runner for page-to-card extraction workflows.
Out of scope: Page list orchestration, processed-document updates, and topic selection.
"""

from __future__ import annotations

import json
import shlex
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from tempfile import gettempdir

from wiki_page_to_cards_types import (
    PageRecord,
    PageResult,
    build_page_result_adapter,
    parse_page_result_payload,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CURSOR_WORKSPACE_ROOT = str(
    Path(gettempdir()) / "knowledge-page-card-orchestration"
)
DEFAULT_WRITE_CARD_COMMAND = [
    str(PROJECT_ROOT / ".venv" / "bin" / "python"),
    str(PROJECT_ROOT / "apps" / "cli" / "main.py"),
]


@dataclass(slots=True)
class PageAgentSettings:
    cursor_agent_command: str = "cursor-agent"
    cursor_agent_workspace_root: str = DEFAULT_CURSOR_WORKSPACE_ROOT
    cursor_agent_timeout_seconds: float = 1800.0
    write_card_command: list[str] = field(
        default_factory=lambda: list(DEFAULT_WRITE_CARD_COMMAND)
    )


def build_write_card_command(settings: PageAgentSettings) -> list[str]:
    return list(settings.write_card_command)


def build_page_agent_prompt(page: PageRecord, write_card_command: list[str]) -> str:
    command_prefix = shlex.join(write_card_command)
    schema = json.dumps(
        build_page_result_adapter(page.page_id).json_schema(),
        ensure_ascii=False,
        indent=2,
    )
    page_payload = json.dumps(
        page.model_dump(mode="json"),
        ensure_ascii=False,
        indent=2,
    )
    return (
        "You are processing one Wikipedia page and extracting atomic knowledge cards.\n"
        "Work only on the provided page.\n"
        "A knowledge card is one self-contained atomic knowledge unit with exactly two fields: title and content.\n"
        "The title must name the knowledge unit precisely, and the content must explain exactly that one unit.\n"
        "Card titles must follow one of these patterns: <subject> or <subject> (<domain>).\n"
        "Prefer <subject> by default.\n"
        "Use the parenthesized <domain> only when minimal domain disambiguation is genuinely necessary.\n"
        "Every card you prepare must satisfy all of these requirements:\n"
        "1. title_validity: the title must be unambiguous, precisely scoped, and independently understandable without additional context.\n"
        "2. title_content_alignment: the title must provide an accurate and sufficient indication of the content's topic.\n"
        "3. title_style_validity: the title must follow the required naming style and must not be a full sentence, a definition-like phrase, a colon-separated explanatory label, or a title with unnecessary qualifiers beyond minimal disambiguation.\n"
        "4. content_coherence: the content must be self-contained and self-explanatory given standard domain terminology, without implicit assumptions, missing context, hidden dependencies, or unresolved references.\n"
        "5. content_atomicity: the content must represent exactly one indivisible knowledge unit and must not mix multiple independent units, even if they are related.\n"
        "6. content_latex_validity: if the content contains LaTeX math, inline math must use \\( and \\), display math must use \\[ and \\], and malformed LaTeX or $ / $$ delimiters are not allowed.\n"
        "Before you run any write command, first plan which cards should be extracted from the page and decide their submission order.\n"
        "Aim to extract about 10 of the most important atomic knowledge cards from the page.\n"
        "Treat 10 as a soft target, not a hard requirement.\n"
        "If the page has fewer worthwhile atomic knowledge units, fewer than 10 cards is acceptable.\n"
        "If the page is long, do not try to exhaustively cover everything; prioritize the most important and most foundational knowledge points.\n"
        "Then submit the planned cards one by one.\n"
        "Use the reviewed card write command for each card you decide to submit.\n"
        "Do not edit files.\n"
        "Do not run commands other than the reviewed card write command.\n"
        "Only after one card returns {\"result\":\"passed\"} may you move to the next planned card.\n"
        "When the command returns {\"result\":\"failed\", ...}, use the rejection details to revise that same candidate and retry it.\n"
        "Do not move to the next planned card until the current candidate passes.\n"
        "If you cannot revise the current candidate into a valid card, end the page as an unsuccessful result.\n"
        "Return ONLY a JSON object that matches the provided JSON Schema exactly.\n"
        "Do not wrap the JSON in markdown.\n"
        "Do not add explanations before or after the JSON.\n\n"
        f"JSON Schema:\n{schema}\n\n"
        f"Reviewed card write command prefix:\n{command_prefix}\n"
        "Append shell-safe --title and --content arguments when calling it.\n\n"
        f"Page:\n{page_payload}\n"
    )


def extract_cursor_result_text(stdout: str) -> str:
    if not stdout.strip():
        raise RuntimeError("cursor-agent returned empty stdout")
    payload = json.loads(stdout)
    if not isinstance(payload, dict):
        raise RuntimeError("cursor-agent outer payload must be a JSON object")
    result = payload.get("result")
    if not isinstance(result, str) or not result.strip():
        raise RuntimeError("cursor-agent payload is missing a non-empty result string")
    return result


def run_page_session(page: PageRecord, settings: PageAgentSettings) -> PageResult:
    write_card_command = build_write_card_command(settings)
    prompt = build_page_agent_prompt(page, write_card_command)
    workspace = Path(settings.cursor_agent_workspace_root) / f"page-{page.page_id}"
    workspace.mkdir(parents=True, exist_ok=True)

    completed = subprocess.run(
        [
            settings.cursor_agent_command,
            "--print",
            "--output-format",
            "json",
            "--sandbox",
            "enabled",
            "--trust",
            "--force",
            "--workspace",
            str(workspace),
            prompt,
        ],
        capture_output=True,
        text=True,
        timeout=settings.cursor_agent_timeout_seconds,
        check=False,
    )
    if completed.returncode != 0:
        stderr = completed.stderr.strip()
        raise RuntimeError(
            f"cursor-agent exited with code {completed.returncode}: {stderr or 'no stderr'}"
        )

    return parse_page_result_payload(page.page_id, extract_cursor_result_text(completed.stdout))
