#!/usr/bin/env python3
"""
One-time production taxonomy reset to the current LCC YAML.

This keeps knowledge graph cards and edges intact, but rebuilds taxonomy-owned
state and assigns all cards to the new Root -> Unclassified leaf.
"""

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from redis.asyncio import Redis
from sqlalchemy import text

from entrypoints.runtime import get_runtime_dependencies
from modules.knowledge_graph.builders import build_knowledge_graph_service
from modules.taxonomy.importer import TaxonomyImporter
from modules.taxonomy.repo import TaxonomyRepo
from modules.taxonomy.root_unclassified_backfill import (
    TaxonomyRootUnclassifiedBackfillService,
)
from modules.taxonomy.view_cache import (
    TAXONOMY_API_VIEW_CACHE_KEY_PREFIX,
    TAXONOMY_VIEW_CACHE_KEY_PREFIX,
)

RESET_TABLES_SQL = """
TRUNCATE TABLE
    taxonomy_classification_webhook_wakeups,
    taxonomy_classification_webhook_events,
    taxonomy_classification_projection_refresh_requests,
    taxonomy_classification_jobs,
    taxonomy_leaf_projection_edges,
    node_taxonomy_assignments,
    taxonomy_nodes
RESTART IDENTITY CASCADE
"""


async def _scalar_count(session, table_name: str) -> int:
    value = await session.scalar(text(f"SELECT count(*) FROM {table_name}"))
    return int(value or 0)


async def _clear_taxonomy_cache(redis_url: str) -> int:
    redis = Redis.from_url(redis_url)
    deleted = 0
    try:
        for pattern in (
            f"{TAXONOMY_VIEW_CACHE_KEY_PREFIX}*",
            f"{TAXONOMY_API_VIEW_CACHE_KEY_PREFIX}*",
        ):
            batch: list[str] = []
            async for key in redis.scan_iter(match=pattern, count=500):
                batch.append(key)
                if len(batch) >= 500:
                    deleted += await redis.delete(*batch)
                    batch.clear()
            if batch:
                deleted += await redis.delete(*batch)
        return deleted
    finally:
        await redis.aclose()


async def _run(yaml_path: Path, *, skip_reset: bool) -> None:
    runtime = get_runtime_dependencies()

    async with runtime.session_factory() as session:
        before = {
            "cards": await _scalar_count(session, "nodes"),
            "graph_edges": await _scalar_count(session, "edges"),
            "taxonomy_nodes": await _scalar_count(session, "taxonomy_nodes"),
            "assignments": await _scalar_count(session, "node_taxonomy_assignments"),
            "projection_edges": await _scalar_count(session, "taxonomy_leaf_projection_edges"),
            "classification_jobs": await _scalar_count(session, "taxonomy_classification_jobs"),
            "webhook_events": await _scalar_count(
                session,
                "taxonomy_classification_webhook_events",
            ),
        }
        print(f"before={before}")

        if skip_reset:
            print("reset_skipped=True")
        else:
            await session.execute(text(RESET_TABLES_SQL))

        importer = TaxonomyImporter(repo=TaxonomyRepo(session=session))
        imported_rows = await importer.import_yaml_file(yaml_path)
        print(f"imported_taxonomy_rows={imported_rows}")

    async with runtime.session_factory() as session:
        taxonomy_repo = TaxonomyRepo(session=session)
        projection_port = build_knowledge_graph_service(
            session=session,
            edge_title_mention_top_k=runtime.settings.edge_title_mention_top_k,
            edge_semantic_top_k=runtime.settings.edge_semantic_top_k,
            edge_semantic_min_strength=runtime.settings.edge_semantic_min_strength,
            edge_semantic_candidate_limit=runtime.settings.edge_semantic_candidate_limit,
        )
        service = TaxonomyRootUnclassifiedBackfillService(
            repo=taxonomy_repo,
            knowledge_projection_port=projection_port,
        )
        result = await service.run(apply=True)
        print(f"backfill={result}")

    async with runtime.session_factory() as session:
        after = {
            "cards": await _scalar_count(session, "nodes"),
            "graph_edges": await _scalar_count(session, "edges"),
            "taxonomy_nodes": await _scalar_count(session, "taxonomy_nodes"),
            "assignments": await _scalar_count(session, "node_taxonomy_assignments"),
            "projection_edges": await _scalar_count(session, "taxonomy_leaf_projection_edges"),
            "classification_jobs": await _scalar_count(session, "taxonomy_classification_jobs"),
            "webhook_events": await _scalar_count(
                session,
                "taxonomy_classification_webhook_events",
            ),
        }
        root_unclassified_assignments = await session.scalar(
            text(
                """
                SELECT count(*)
                FROM node_taxonomy_assignments
                WHERE taxonomy_node_id = (
                    SELECT child.id
                    FROM taxonomy_nodes child
                    JOIN taxonomy_nodes root ON root.id = child.parent_id
                    WHERE root.parent_id IS NULL
                      AND root.name = 'Root'
                      AND child.name = 'Unclassified'
                )
                """
            )
        )
        top_level_names = (
            await session.execute(
                text(
                    """
                    SELECT name
                    FROM taxonomy_nodes
                    WHERE parent_id = 1
                      AND name <> 'Unclassified'
                    ORDER BY id
                    """
                )
            )
        ).scalars().all()
        print(f"after={after}")
        print(f"root_unclassified_assignments={int(root_unclassified_assignments or 0)}")
        print(f"top_level_count={len(top_level_names)}")
        print(f"top_level_names={list(top_level_names)}")

    deleted_cache_keys = await _clear_taxonomy_cache(runtime.settings.redis_url)
    print(f"deleted_taxonomy_cache_keys={deleted_cache_keys}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--yaml-path", required=True, type=Path)
    parser.add_argument("--confirm-prod-taxonomy-reset", action="store_true")
    parser.add_argument("--skip-reset", action="store_true")
    args = parser.parse_args()

    if not args.confirm_prod_taxonomy_reset:
        raise SystemExit("--confirm-prod-taxonomy-reset is required")
    if not args.yaml_path.is_file():
        raise SystemExit(f"YAML file not found: {args.yaml_path}")

    asyncio.run(_run(args.yaml_path, skip_reset=args.skip_reset))


if __name__ == "__main__":
    main()
