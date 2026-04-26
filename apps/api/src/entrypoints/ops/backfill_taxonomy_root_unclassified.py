"""
Abstract: Operator CLI for one-time Root Unclassified taxonomy assignment backfill.
Out of scope: API serving, schema migration, and job-queue classification runtime.
"""

from __future__ import annotations

import asyncio

import click

from entrypoints.runtime import get_runtime_dependencies
from modules.knowledge_graph.builders import build_knowledge_graph_service
from modules.taxonomy.repo import TaxonomyRepo
from modules.taxonomy.root_unclassified_backfill import (
    TaxonomyRootUnclassifiedBackfillResult,
    TaxonomyRootUnclassifiedBackfillService,
)


async def run_backfill(*, apply: bool) -> TaxonomyRootUnclassifiedBackfillResult:
    runtime = get_runtime_dependencies()
    async with runtime.session_factory() as session:
        taxonomy_repo = TaxonomyRepo(session=session)
        projection_port = (
            build_knowledge_graph_service(
                session=session,
                edge_similarity_top_k=runtime.settings.edge_similarity_top_k,
                edge_similarity_min_strength=runtime.settings.edge_similarity_min_strength,
            )
            if apply
            else None
        )
        service = TaxonomyRootUnclassifiedBackfillService(
            repo=taxonomy_repo,
            knowledge_projection_port=projection_port,
        )
        return await service.run(apply=apply)


def _print_result(result: TaxonomyRootUnclassifiedBackfillResult) -> None:
    click.echo(f"mode={result.mode}")
    click.echo(f"root_id={result.root_id}")
    click.echo(f"root_unclassified_id={result.root_unclassified_id}")
    click.echo(f"total_cards={result.total_cards}")
    click.echo(f"assigned_before={result.assigned_before}")
    click.echo(f"missing_before={result.missing_before}")
    click.echo(f"inserted_assignments={result.inserted_assignments}")
    click.echo(f"missing_after={result.missing_after}")
    click.echo(f"projection_rebuilt={result.projection_rebuilt}")


@click.command()
@click.option(
    "--apply",
    "apply_changes",
    is_flag=True,
    default=False,
    help="Apply the backfill. Omit for a read-only dry run.",
)
@click.option(
    "--confirm-backfill",
    is_flag=True,
    default=False,
    help="Required with --apply to confirm historical card assignment writes.",
)
def cli(*, apply_changes: bool, confirm_backfill: bool) -> None:
    if apply_changes and not confirm_backfill:
        raise click.ClickException("--apply requires --confirm-backfill.")

    result = asyncio.run(run_backfill(apply=apply_changes))
    _print_result(result)


if __name__ == "__main__":
    cli()
