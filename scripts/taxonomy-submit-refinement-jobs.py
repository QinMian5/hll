#!/usr/bin/env python3
"""
Abstract: Operator CLI for submitting taxonomy refinement jobs to job-queue-mcp.
Out of scope: Result processing, webhook serving, and taxonomy child creation.
"""

from __future__ import annotations

import asyncio

import click
import httpx
from job_queue_mcp_client.auth import ClientCredentialsTokenProvider
from job_queue_mcp_client.producer import (
    AsyncClient as TaxonomyClassificationJobQueueClient,
)

from core.config import load_taxonomy_classification_runtime_settings
from modules.taxonomy_classification.dto import (
    TaxonomyClassificationSubmissionResult,
    TaxonomyClassificationSubmissionSelection,
)
from modules.taxonomy_classification.submission import (
    TaxonomyClassificationSubmissionService,
)
from shared.db.session import build_async_engine, build_async_session_factory


async def submit_refinement_jobs(
    *,
    selection: TaxonomyClassificationSubmissionSelection,
    limit: int | None,
) -> TaxonomyClassificationSubmissionResult:
    settings = load_taxonomy_classification_runtime_settings()
    engine = build_async_engine(database_url=settings.database_url)
    session_factory = build_async_session_factory(engine=engine)
    job_queue_token_http_client = httpx.AsyncClient()
    job_queue_client = TaxonomyClassificationJobQueueClient(
        base_url=settings.taxonomy_classification_job_queue_base_url,
        token_provider=ClientCredentialsTokenProvider(
            token_url=settings.taxonomy_classification_job_queue_token_url,
            client_id=settings.taxonomy_classification_job_queue_client_id,
            client_secret=settings.taxonomy_classification_job_queue_client_secret,
            resource=settings.taxonomy_classification_job_queue_resource,
            scope=settings.taxonomy_classification_job_queue_scopes,
            http_client=job_queue_token_http_client,
        ),
    )
    try:
        async with session_factory() as session:
            service = TaxonomyClassificationSubmissionService(
                session,
                job_queue_client=job_queue_client,
                queue_name=settings.taxonomy_classification_queue_name,
            )
            result = await service.submit_refinement_jobs(
                selection=selection,
                limit=limit,
            )
            await session.commit()
            return result
    finally:
        await job_queue_client.aclose()
        await job_queue_token_http_client.aclose()
        await engine.dispose()


@click.command()
@click.option(
    "--scope-name",
    type=str,
    default=None,
    help="Case-insensitive regular taxonomy node name. Fails when the name is ambiguous.",
)
@click.option(
    "--scope-path",
    type=str,
    default=None,
    help="Case-insensitive root-to-node path separated by '/'. Example: Root / Science.",
)
@click.option(
    "--all-unclassified",
    is_flag=True,
    help="Scan all taxonomy nodes that have a direct Unclassified leaf.",
)
@click.option(
    "--limit",
    type=click.IntRange(min=1),
    default=None,
    help="Submit only the first N cards currently assigned to the scope Unclassified leaf.",
)
def cli(
    scope_name: str | None,
    scope_path: str | None,
    all_unclassified: bool,
    limit: int | None,
) -> None:
    try:
        selection = _build_selection(
            scope_name=scope_name,
            scope_path=scope_path,
            all_unclassified=all_unclassified,
        )
        result = asyncio.run(submit_refinement_jobs(selection=selection, limit=limit))
    except click.ClickException:
        raise
    except Exception as exc:
        raise click.ClickException(str(exc)) from exc

    click.echo(_format_result(result))


def _build_selection(
    *,
    scope_name: str | None,
    scope_path: str | None,
    all_unclassified: bool,
) -> TaxonomyClassificationSubmissionSelection:
    selector_count = sum(
        [
            scope_name is not None,
            scope_path is not None,
            all_unclassified,
        ]
    )
    if selector_count != 1:
        raise click.UsageError(
            "Choose exactly one scope selector: --scope-name, --scope-path, or --all-unclassified."
        )
    if scope_name is not None:
        return TaxonomyClassificationSubmissionSelection(
            kind="scope_name",
            scope_name=scope_name,
        )
    if scope_path is not None:
        return TaxonomyClassificationSubmissionSelection(
            kind="scope_path",
            scope_path=_parse_scope_path(scope_path),
        )
    return TaxonomyClassificationSubmissionSelection(kind="all_unclassified")


def _parse_scope_path(raw_scope_path: str) -> tuple[str, ...]:
    path = tuple(
        segment.strip() for segment in raw_scope_path.split("/") if segment.strip()
    )
    if not path:
        raise click.BadParameter("scope path must include at least one node name")
    return path


def _format_result(result: TaxonomyClassificationSubmissionResult) -> str:
    lines = [
        f"Selected scopes: {result.selected_scope_count}",
        f"Submitted: {result.submitted_count}",
        f"Already linked: {result.already_linked_count}",
        f"Skipped no children: {result.skipped_no_children}",
    ]
    if result.scopes:
        lines.append("Scopes:")
        for scope in result.scopes:
            breadcrumb = " / ".join(scope.breadcrumb)
            skipped = str(scope.skipped_no_children).lower()
            lines.append(
                f"- {breadcrumb}: submitted={scope.submitted_count}, "
                f"already_linked={scope.already_linked_count}, "
                f"regular_children={scope.regular_child_count}, "
                f"skipped_no_children={skipped}"
            )
    return "\n".join(lines)


if __name__ == "__main__":
    cli()
