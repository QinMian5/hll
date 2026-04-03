"""
Abstract: Single-file Click CLI for agent-reviewed knowledge card submission.
Out of scope: Multi-file packaging, test coverage, and lint workflow integration.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from typing import Annotated

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


@dataclass
class ReviewState:
    title: str
    content: str
    review: ReviewResult | None = None


@dataclass
class CliDeps:
    reviewer_agent: Agent
    submit_card: Callable[[str, str], None]


@dataclass
class ReviewCardNode(BaseNode[ReviewState, CliDeps, ReviewResult]):
    async def run(
        self,
        ctx: GraphRunContext[ReviewState, CliDeps],
    ) -> SubmitCardNode | End[ReviewResult]:
        result = await ctx.deps.reviewer_agent.run(
            f"Title:\n{ctx.state.title}\n\nContent:\n{ctx.state.content}"
        )
        review = result.output
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


def build_reviewer_agent(settings: CliSettings) -> Agent:
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
            reviewer_agent=build_reviewer_agent(settings),
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
