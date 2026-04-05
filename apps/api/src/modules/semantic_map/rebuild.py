"""
Abstract: Semantic-map rebuild orchestration from taxonomy structure and
knowledge embeddings to snapshot artifacts.
Out of scope: FastAPI transport wiring and SQLAlchemy query execution details.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from datetime import UTC, datetime

from modules.knowledge_graph.ports import KnowledgeGraphProjectionPort
from modules.semantic_map.dto import DefaultView, SemanticMapManifest
from modules.semantic_map.metadata import (
    DEFAULT_TILE_SIZE,
    DEFAULT_VIEW_TARGET,
    WORLD_BOUNDS,
    SemanticLevelDefinition,
    build_semantic_levels_from_leaf_depths,
)
from modules.semantic_map.ports import SemanticMapSnapshotWritePort, TaxonomySemanticMapPort
from modules.semantic_map.rebuild_projection import project_points
from modules.semantic_map.rebuild_tiling import build_tiles
from modules.semantic_map.rebuild_topology import build_taxonomy_region_levels


def _utc_now() -> datetime:
    return datetime.now(UTC).replace(microsecond=0)


def _snapshot_version_from_datetime(moment: datetime) -> str:
    return moment.astimezone(UTC).strftime("%Y%m%d_%H%M%S_%f")


class SemanticMapRebuildService:
    def __init__(
        self,
        *,
        projection_port: KnowledgeGraphProjectionPort,
        taxonomy_port: TaxonomySemanticMapPort,
        snapshot_repo: SemanticMapSnapshotWritePort,
        now: Callable[[], datetime] = _utc_now,
        semantic_levels: Sequence[SemanticLevelDefinition] | None = None,
    ) -> None:
        self._projection_port = projection_port
        self._taxonomy_port = taxonomy_port
        self._snapshot_repo = snapshot_repo
        self._now = now
        self._semantic_levels = tuple(semantic_levels) if semantic_levels is not None else None

    async def rebuild_current_snapshot(self) -> str | None:
        assignments = await self._taxonomy_port.list_semantic_map_assignments()
        if not assignments:
            return None

        semantic_levels = await self._resolve_semantic_levels()
        if not semantic_levels:
            return None

        assigned_node_ids = sorted({assignment.node_id for assignment in assignments})
        nodes = await self._projection_port.list_projection_nodes_for_node_ids(
            node_ids=assigned_node_ids,
        )
        if not nodes:
            return None
        ordered_nodes = sorted(nodes, key=lambda node: node.node_id)

        taxonomy_nodes = await self._taxonomy_port.list_tree_nodes_for_semantic_map()
        if not taxonomy_nodes:
            return None

        built_at = self._now()
        version = _snapshot_version_from_datetime(built_at)
        projected_points = project_points(ordered_nodes)
        region_levels, card_points = build_taxonomy_region_levels(
            projection_nodes=ordered_nodes,
            projected_points=projected_points,
            taxonomy_nodes=taxonomy_nodes,
            assignments=assignments,
            semantic_levels=semantic_levels,
        )
        if not card_points:
            return None
        tiles = build_tiles(
            region_levels=region_levels,
            card_points=card_points,
            semantic_levels=semantic_levels,
            world_bounds=WORLD_BOUNDS,
        )
        manifest = SemanticMapManifest(
            version=version,
            schema_version=version,
            built_at=built_at,
            world_bounds=WORLD_BOUNDS,
            tile_size=DEFAULT_TILE_SIZE,
            max_zoom=max(level.max_zoom for level in semantic_levels),
            default_view=DefaultView(target=DEFAULT_VIEW_TARGET, zoom=0.0),
            default_semantic_level=semantic_levels[0].level,
            semantic_levels=list(semantic_levels),
        )
        await self._snapshot_repo.publish_snapshot(
            manifest=manifest,
            tiles=tiles,
        )
        return version

    async def _resolve_semantic_levels(self) -> tuple[SemanticLevelDefinition, ...]:
        if self._semantic_levels is not None:
            return self._semantic_levels

        leaf_depths = await self._taxonomy_port.list_assigned_leaf_depths_for_semantic_map()
        return build_semantic_levels_from_leaf_depths(leaf_depths=leaf_depths)
