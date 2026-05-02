#!/usr/bin/env python3
"""
Abstract: Operator CLI for submitting taxonomy refinement jobs to job-queue-mcp.
Out of scope: Result processing, webhook serving, and taxonomy child creation.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Callable

import click
import httpx
from job_queue_mcp_client.auth import ClientCredentialsTokenProvider
from job_queue_mcp_client.producer import (
    AsyncClient as TaxonomyClassificationJobQueueClient,
)
from rich.console import Console
from rich.progress import (
    BarColumn,
    Progress,
    TaskID,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
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
    batch_size: int,
    progress_total_callback: Callable[[int], None] | None = None,
    progress_advance_callback: Callable[[int], None] | None = None,
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
                batch_size=batch_size,
                progress_total_callback=progress_total_callback,
                progress_advance_callback=progress_advance_callback,
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
    "--all-direct-assignments",
    is_flag=True,
    help="Scan all taxonomy nodes that have direct card assignments.",
)
@click.option(
    "--limit",
    type=click.IntRange(min=1),
    default=None,
    help="Submit only the first N cards currently assigned directly to selected scopes.",
)
@click.option(
    "--batch-size",
    type=click.IntRange(min=1, max=1000),
    default=1000,
    show_default=True,
    help=(
        "Maximum producer jobs per request. Request bodies are also "
        "auto-split below the 900 KiB producer body cap."
    ),
)
@click.option(
    "--verbose",
    is_flag=True,
    help="Include per-scope submission details after the compact summary.",
)
def cli(
    scope_name: str | None,
    scope_path: str | None,
    all_direct_assignments: bool,
    limit: int | None,
    batch_size: int,
    verbose: bool,
) -> None:
    started_at = time.perf_counter()
    try:
        selection = _build_selection(
            scope_name=scope_name,
            scope_path=scope_path,
            all_direct_assignments=all_direct_assignments,
        )
        stdout = click.get_text_stream("stdout")
        if stdout.isatty():
            console = Console(file=stdout)
            with Progress(
                TextColumn("{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                TimeElapsedColumn(),
                console=console,
            ) as progress:
                task_id: TaskID | None = None

                def set_total(total: int) -> None:
                    nonlocal task_id
                    task_id = progress.add_task("Submitting taxonomy jobs", total=total)

                def advance(delta: int) -> None:
                    if task_id is not None:
                        progress.advance(task_id, delta)

                result = asyncio.run(
                    submit_refinement_jobs(
                        selection=selection,
                        limit=limit,
                        batch_size=batch_size,
                        progress_total_callback=set_total,
                        progress_advance_callback=advance,
                    )
                )
        else:
            result = asyncio.run(
                submit_refinement_jobs(
                    selection=selection,
                    limit=limit,
                    batch_size=batch_size,
                )
            )
    except click.ClickException:
        raise
    except Exception as exc:
        raise click.ClickException(str(exc)) from exc

    click.echo(
        _format_result(
            result,
            elapsed_seconds=time.perf_counter() - started_at,
            verbose=verbose,
        )
    )


def _build_selection(
    *,
    scope_name: str | None,
    scope_path: str | None,
    all_direct_assignments: bool,
) -> TaxonomyClassificationSubmissionSelection:
    selector_count = sum(
        [
            scope_name is not None,
            scope_path is not None,
            all_direct_assignments,
        ]
    )
    if selector_count != 1:
        raise click.UsageError(
            "Choose exactly one scope selector: --scope-name, --scope-path, "
            "or --all-direct-assignments."
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
    return TaxonomyClassificationSubmissionSelection(kind="all_direct_assignments")


def _parse_scope_path(raw_scope_path: str) -> tuple[str, ...]:
    path = tuple(segment.strip() for segment in raw_scope_path.split("/") if segment.strip())
    if not path:
        raise click.BadParameter("scope path must include at least one node name")
    return path


def _format_result(
    result: TaxonomyClassificationSubmissionResult,
    *,
    elapsed_seconds: float,
    verbose: bool,
) -> str:
    linked_count = result.submitted_count + result.reused_idempotent_count
    jobs_per_second = linked_count / elapsed_seconds if elapsed_seconds > 0 else 0.0
    lines = [
        f"Selected scopes: {result.selected_scope_count}",
        f"Submitted: {result.submitted_count}",
        f"Reused idempotent: {result.reused_idempotent_count}",
        f"Already linked: {result.already_linked_count}",
        f"Skipped no children: {result.skipped_no_children}",
        f"Elapsed seconds: {elapsed_seconds:.2f}",
        f"Effective jobs/sec: {jobs_per_second:.2f}",
    ]
    if verbose and result.scopes:
        lines.append("Scopes:")
        for scope in result.scopes:
            breadcrumb = " / ".join(scope.breadcrumb)
            skipped = str(scope.skipped_no_children).lower()
            lines.append(
                f"- {breadcrumb}: submitted={scope.submitted_count}, "
                f"reused_idempotent={scope.reused_idempotent_count}, "
                f"already_linked={scope.already_linked_count}, "
                f"regular_children={scope.regular_child_count}, "
                f"skipped_no_children={skipped}"
            )
    return "\n".join(lines)


if __name__ == "__main__":
    cli()
