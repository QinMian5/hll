"""
Abstract: Single-file Click CLI for agent-reviewed knowledge card submission.
Out of scope: Multi-file packaging, test coverage, and lint workflow integration.
"""

from __future__ import annotations

import json
import subprocess
from tempfile import gettempdir
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Literal

import click
import httpx
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    ValidationError,
    model_validator,
)
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_graph import BaseNode, End, Graph, GraphRunContext


NonEmptyText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
NullableReason = (
    Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)] | None
)
DEFAULT_CURSOR_WORKSPACE = str(Path(gettempdir()) / "knowledge-cli-cursor-review")

REVIEWER_INSTRUCTIONS = """
Review the provided title and content as a candidate knowledge card.
Return the structured result exactly as defined by the output schema.
""".strip()


class StrictModel(BaseModel):
    model_config = ConfigDict(
        strict=True,
        extra="forbid",
        str_strip_whitespace=True,
    )


class ReviewItem(StrictModel):
    passed: bool = Field(
        description="Whether this review dimension passes.",
    )
    reason: NullableReason = Field(
        default=None,
        description=(
            "Why this review dimension failed. Explain the judgment only and do not include "
            "rewrite advice or improvement suggestions. Null is allowed only when passed is true."
        ),
    )

    @model_validator(mode="after")
    def validate_reason(self) -> ReviewItem:
        if self.passed:
            return self
        if self.reason is None:
            raise ValueError("reason must be present when passed is false")
        return self


class ReviewResult(StrictModel):
    title_validity: ReviewItem = Field(
        description=(
            "Whether the title is unambiguous, precisely scoped, and independently understandable "
            "without requiring additional context. Reject titles that depend on missing context, "
            "are ambiguously scoped, or cannot stand alone as clear node titles."
        ),
    )
    title_content_alignment: ReviewItem = Field(
        description=(
            "Whether the title provides an accurate and sufficient indication of the content's topic. "
            "Reject titles that point to a different topic, misstate the topic, or are too broad or "
            "too narrow to indicate what the content is actually about."
        ),
    )
    content_coherence: ReviewItem = Field(
        description=(
            "Whether the content is self-contained and self-explanatory given standard domain "
            "terminology, which is allowed. Reject content whose correct interpretation requires "
            "implicit assumptions, missing context, hidden dependencies, or unresolved references."
        ),
    )
    content_atomicity: ReviewItem = Field(
        description=(
            "Whether the content represents exactly one indivisible knowledge unit, "
            "expressing a single concept that cannot be meaningfully decomposed into smaller "
            "independent units. Reject content that can be meaningfully decomposed into multiple "
            "smaller independent units, even if they are related."
        ),
    )
    content_latex_validity: ReviewItem = Field(
        description=(
            "Whether LaTeX expressions in the content, if any, use standard and syntactically "
            "correct LaTeX math delimiters and notation. Inline math must use \\( and \\), and "
            "display math must use \\[ and \\]. Reject content that uses $ or $$ delimiters, "
            "mismatched delimiters, or malformed LaTeX math syntax."
        ),
    )

    def passed(self) -> bool:
        return all(
            item.passed
            for item in (
                self.title_validity,
                self.title_content_alignment,
                self.content_coherence,
                self.content_atomicity,
                self.content_latex_validity,
            )
        )


Reviewer = Callable[[str, str], ReviewResult]


def serialize_review_result(review: ReviewResult) -> str:
    if review.passed():
        return json.dumps({"result": "passed"}, ensure_ascii=False, indent=4)

    failures: dict[str, dict[str, str | None]] = {}

    for field_name, field_info in ReviewResult.model_fields.items():
        item = getattr(review, field_name)
        if item.passed:
            continue

        failure_payload: dict[str, str | None] = {
            "reason": item.reason,
        }
        if field_info.description is not None:
            failure_payload["hint"] = field_info.description
        failures[field_name] = failure_payload

    return json.dumps(
        {
            "result": "failed",
            "failures": failures,
        },
        ensure_ascii=False,
        indent=4,
    )


class CardInput(StrictModel):
    title: NonEmptyText = Field(
        description="Knowledge card title.",
    )
    content: NonEmptyText = Field(
        description="Knowledge card content.",
    )


class CliSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="KNOWLEDGE_CLI_",
        extra="ignore",
        str_strip_whitespace=True,
    )

    cards_url: str = Field(
        default="http://127.0.0.1:8000/cards",
        description="Absolute URL of the ingestion cards endpoint.",
    )
    review_backend: Literal["cursor-agent", "openai"] = Field(
        default="cursor-agent",
        description="Reviewer backend used to evaluate the card before submission.",
    )
    review_model: str = Field(
        default="gpt-5.4",
        description="OpenAI-compatible model identifier used by the reviewer agent.",
    )
    review_api_key: str = Field(
        default="knowledge-graph-h0vjxHXlCdodjFORr",
        description="API key used for the OpenAI-compatible reviewer endpoint.",
    )
    review_base_url: str = Field(
        default="https://api.orbitalis.org/v1",
        description="Base URL of the OpenAI-compatible reviewer endpoint.",
    )
    request_timeout_seconds: float = Field(
        default=10.0,
        gt=0,
        description="HTTP timeout used when issuing the ingestion submission call.",
    )
    cursor_agent_command: str = Field(
        default="cursor-agent",
        description="Executable used to invoke Cursor Agent in headless mode.",
    )
    cursor_agent_workspace: str = Field(
        default=DEFAULT_CURSOR_WORKSPACE,
        description="Workspace passed to Cursor Agent while reviewing the card.",
    )
    cursor_agent_timeout_seconds: float = Field(
        default=180.0,
        gt=0,
        description="Timeout used for a single Cursor Agent review attempt.",
    )
    cursor_agent_max_retries: int = Field(
        default=3,
        ge=1,
        description="Maximum number of Cursor Agent retries before failing the review.",
    )


@dataclass
class ReviewState:
    title: str
    content: str
    review: ReviewResult | None = None


@dataclass
class CliDeps:
    reviewer: Reviewer
    submit_card: Callable[[str, str], None]


@dataclass
class ReviewCardNode(BaseNode[ReviewState, CliDeps, ReviewResult]):
    async def run(
        self,
        ctx: GraphRunContext[ReviewState, CliDeps],
    ) -> SubmitCardNode | End[ReviewResult]:
        review = ctx.deps.reviewer(ctx.state.title, ctx.state.content)
        ctx.state.review = review
        if not review.passed():
            return End(review)
        return SubmitCardNode()


@dataclass
class SubmitCardNode(BaseNode[ReviewState, CliDeps, ReviewResult]):
    async def run(
        self,
        ctx: GraphRunContext[ReviewState, CliDeps],
    ) -> End[ReviewResult]:
        review = ctx.state.review
        if review is None:
            raise RuntimeError("review result is missing before submission")
        ctx.deps.submit_card(ctx.state.title, ctx.state.content)
        return End(review)


def build_openai_reviewer_agent(settings: CliSettings) -> Agent:
    model = OpenAIChatModel(
        settings.review_model,
        provider=OpenAIProvider(
            base_url=settings.review_base_url,
            api_key=settings.review_api_key,
        ),
    )
    return Agent(
        model,
        output_type=ReviewResult,
        instructions=REVIEWER_INSTRUCTIONS,
    )


def build_card_review_message(title: str, content: str) -> str:
    return f"Title:\n{title}\n\nContent:\n{content}"


def build_cursor_review_prompt(title: str, content: str) -> str:
    schema = json.dumps(ReviewResult.model_json_schema(), ensure_ascii=False, indent=2)
    payload = json.dumps(
        {"title": title, "content": content},
        ensure_ascii=False,
        indent=2,
    )
    return (
        "Review the following knowledge card.\n"
        "Return ONLY a JSON object that matches the provided JSON Schema exactly.\n"
        "Do not wrap the JSON in markdown.\n"
        "Do not add explanations before or after the JSON.\n"
        "If a field passes, set reason to null.\n"
        "If a field fails, provide a concise reason.\n\n"
        f"JSON Schema:\n{schema}\n\n"
        f"Knowledge card:\n{payload}\n"
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


def run_cursor_review_once(title: str, content: str, settings: CliSettings) -> ReviewResult:
    prompt = build_cursor_review_prompt(title, content)
    workspace = Path(settings.cursor_agent_workspace)
    workspace.mkdir(parents=True, exist_ok=True)
    completed = subprocess.run(
        [
            settings.cursor_agent_command,
            "--print",
            "--output-format",
            "json",
            "--mode",
            "ask",
            "--sandbox",
            "enabled",
            "--trust",
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
    return ReviewResult.model_validate_json(extract_cursor_result_text(completed.stdout))


def run_cursor_review(title: str, content: str, settings: CliSettings) -> ReviewResult:
    last_error: Exception | None = None
    for _ in range(settings.cursor_agent_max_retries):
        try:
            return run_cursor_review_once(title, content, settings)
        except Exception as exc:
            last_error = exc
    raise RuntimeError(
        f"cursor-agent review failed after {settings.cursor_agent_max_retries} attempts"
    ) from last_error


def build_openai_reviewer(settings: CliSettings) -> Reviewer:
    reviewer_agent = build_openai_reviewer_agent(settings)

    def review(title: str, content: str) -> ReviewResult:
        result = reviewer_agent.run_sync(build_card_review_message(title, content))
        return result.output

    return review


def build_cursor_reviewer(settings: CliSettings) -> Reviewer:
    def review(title: str, content: str) -> ReviewResult:
        return run_cursor_review(title, content, settings)

    return review


def build_reviewer(settings: CliSettings) -> Reviewer:
    if settings.review_backend == "openai":
        return build_openai_reviewer(settings)
    return build_cursor_reviewer(settings)


def build_submitter(settings: CliSettings) -> Callable[[str, str], None]:
    def submit_card(title: str, content: str) -> None:
        with httpx.Client(timeout=settings.request_timeout_seconds) as client:
            client.post(
                settings.cards_url,
                json={"title": title, "content": content},
            )

    return submit_card


def run_review_graph(payload: CardInput, settings: CliSettings) -> ReviewResult:
    graph = Graph(nodes=[ReviewCardNode, SubmitCardNode])
    result = graph.run_sync(
        ReviewCardNode(),
        state=ReviewState(title=payload.title, content=payload.content),
        deps=CliDeps(
            reviewer=build_reviewer(settings),
            submit_card=build_submitter(settings),
        ),
    )
    return result.output


@click.command()
@click.option("--title", required=True, type=str, help="Knowledge card title.")
@click.option("--content", required=True, type=str, help="Knowledge card content.")
def cli(title: str, content: str) -> None:
    try:
        payload = CardInput(title=title, content=content)
        settings = CliSettings()
        review = run_review_graph(payload, settings)
    except ValidationError as exc:
        raise click.ClickException(str(exc)) from exc
    except Exception as exc:
        raise click.ClickException(str(exc)) from exc

    click.echo(serialize_review_result(review))
    raise SystemExit(0 if review.passed() else 1)


if __name__ == "__main__":
    cli()
