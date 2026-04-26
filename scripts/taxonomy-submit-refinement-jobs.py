#!/usr/bin/env python3
"""
Abstract: Operator CLI for submitting taxonomy refinement jobs to job-queue-mcp.
Out of scope: Result processing, webhook serving, and taxonomy child creation.
"""

from __future__ import annotations

import asyncio

import click

from core.config import load_taxonomy_classification_runtime_settings
from modules.taxonomy_classification.job_queue_client import (
    TaxonomyClassificationJobQueueClient,
)
from modules.taxonomy_classification.job_queue_token import (
    ClientCredentialsTokenProvider,
)
from modules.taxonomy_classification.submission import (
    TaxonomyClassificationSubmissionService,
)
from shared.db.session import build_async_engine, build_async_session_factory


async def submit_refinement_jobs(*, scope_node_id: int, limit: int | None) -> int:
    settings = load_taxonomy_classification_runtime_settings()
    engine = build_async_engine(database_url=settings.database_url)
    session_factory = build_async_session_factory(engine=engine)
    job_queue_client = TaxonomyClassificationJobQueueClient(
        base_url=settings.taxonomy_classification_job_queue_base_url,
        token_provider=ClientCredentialsTokenProvider(
            token_url=settings.taxonomy_classification_job_queue_token_url,
            client_id=settings.taxonomy_classification_job_queue_client_id,
            client_secret=settings.taxonomy_classification_job_queue_client_secret,
            resource=settings.taxonomy_classification_job_queue_resource,
            scope=settings.taxonomy_classification_job_queue_scopes,
        ),
    )
    try:
        async with session_factory() as session:
            service = TaxonomyClassificationSubmissionService(
                session,
                job_queue_client=job_queue_client,
                queue_name=settings.taxonomy_classification_queue_name,
            )
            submitted_count = await service.submit_scope_refinement_jobs(
                scope_node_id=scope_node_id,
                limit=limit,
            )
            await session.commit()
            return submitted_count
    finally:
        await job_queue_client.aclose()
        await engine.dispose()


@click.command()
@click.option(
    "--scope-node-id",
    type=click.IntRange(min=1),
    required=True,
    help="Regular taxonomy node whose direct Unclassified child should be refined.",
)
@click.option(
    "--limit",
    type=click.IntRange(min=1),
    default=None,
    help="Submit only the first N cards currently assigned to the scope Unclassified leaf.",
)
def cli(scope_node_id: int, limit: int | None) -> None:
    try:
        submitted_count = asyncio.run(
            submit_refinement_jobs(scope_node_id=scope_node_id, limit=limit)
        )
    except Exception as exc:
        raise click.ClickException(str(exc)) from exc

    click.echo(f"Submitted {submitted_count} taxonomy classification jobs.")


if __name__ == "__main__":
    cli()
