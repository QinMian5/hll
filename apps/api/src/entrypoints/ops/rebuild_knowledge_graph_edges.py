"""
Abstract: Operator CLI for dry-running or applying deterministic graph edge rebuilds.
Out of scope: API serving, worker actors, and database migration execution.
"""

from __future__ import annotations

import asyncio
from typing import cast

import click
from redis.asyncio import Redis

from entrypoints.runtime import get_runtime_dependencies
from modules.knowledge_graph.builders import build_knowledge_graph_service
from modules.knowledge_graph.edge_rebuild import (
    EdgeRebuildResult,
    rebuild_knowledge_graph_edges_bulk,
)
from modules.knowledge_graph.repo import KnowledgeRepo
from modules.taxonomy.projection_rebuild import rebuild_taxonomy_leaf_projection_edges
from modules.taxonomy.repo import TaxonomyRepo
from modules.taxonomy.view_cache import TaxonomyRedisProtocol, TaxonomyViewRedisCache


async def run_rebuild(
    *,
    apply: bool,
    edge_semantic_top_k: int | None,
    edge_semantic_min_strength: float | None,
) -> EdgeRebuildResult:
    runtime = get_runtime_dependencies()
    top_k = (
        edge_semantic_top_k
        if edge_semantic_top_k is not None
        else runtime.settings.edge_semantic_top_k
    )
    min_strength = (
        edge_semantic_min_strength
        if edge_semantic_min_strength is not None
        else runtime.settings.edge_semantic_min_strength
    )

    async with runtime.session_factory() as session:
        try:
            result = await rebuild_knowledge_graph_edges_bulk(
                repo=KnowledgeRepo(session=session),
                edge_semantic_top_k=top_k,
                edge_semantic_min_strength=min_strength,
                apply=apply,
            )

            if apply:
                taxonomy_repo = TaxonomyRepo(session=session)
                taxonomy_view_cache = TaxonomyViewRedisCache(
                    redis=cast(
                        TaxonomyRedisProtocol,
                        Redis.from_url(runtime.settings.redis_url),
                    )
                )
                knowledge_projection_port = build_knowledge_graph_service(
                    session=session,
                    edge_title_mention_top_k=runtime.settings.edge_title_mention_top_k,
                    edge_semantic_top_k=top_k,
                    edge_semantic_min_strength=min_strength,
                    edge_semantic_candidate_limit=(runtime.settings.edge_semantic_candidate_limit),
                    taxonomy_view_cache=taxonomy_view_cache,
                )
                await rebuild_taxonomy_leaf_projection_edges(
                    repo=taxonomy_repo,
                    projection_port=knowledge_projection_port,
                    view_cache=taxonomy_view_cache,
                )
                await session.commit()
            else:
                await session.rollback()

            return result
        except Exception:
            await session.rollback()
            raise


def _print_result(
    *,
    result: EdgeRebuildResult,
) -> None:
    mode = "apply" if result.applied else "dry-run"
    click.echo(f"mode={mode}")
    click.echo(f"top_k={result.edge_semantic_top_k}")
    click.echo(f"min_strength={result.edge_semantic_min_strength}")
    click.echo(f"node_count={result.node_count}")
    click.echo(f"planned_edge_count={result.planned_edge_count}")
    click.echo(f"inserted_edge_count={result.inserted_edge_count}")
    if not result.applied:
        click.echo("No database writes performed. Re-run with --apply to rebuild edges.")


@click.command()
@click.option(
    "--apply",
    "apply_changes",
    is_flag=True,
    default=False,
    help="Apply the rebuild. Omit for a read-only dry run.",
)
@click.option(
    "--confirm-writers-paused",
    is_flag=True,
    default=False,
    help="Required with --apply after pausing API/worker writes to the graph.",
)
@click.option(
    "--top-k",
    "edge_semantic_top_k",
    type=click.IntRange(min=1),
    default=None,
    help="Override KNOWLEDGE_API_EDGE_SEMANTIC_TOP_K.",
)
@click.option(
    "--min-strength",
    "edge_semantic_min_strength",
    type=click.FloatRange(min=0.0, max=1.0),
    default=None,
    help="Override KNOWLEDGE_API_EDGE_SEMANTIC_MIN_STRENGTH.",
)
def cli(
    *,
    apply_changes: bool,
    confirm_writers_paused: bool,
    edge_semantic_top_k: int | None,
    edge_semantic_min_strength: float | None,
) -> None:
    if apply_changes and not confirm_writers_paused:
        raise click.ClickException("--apply requires --confirm-writers-paused.")

    result = asyncio.run(
        run_rebuild(
            apply=apply_changes,
            edge_semantic_top_k=edge_semantic_top_k,
            edge_semantic_min_strength=edge_semantic_min_strength,
        )
    )
    _print_result(
        result=result,
    )


if __name__ == "__main__":
    cli()
