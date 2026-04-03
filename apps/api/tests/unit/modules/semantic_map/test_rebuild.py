"""
Abstract: Unit tests for semantic-map rebuild orchestration and geometry helpers.
Out of scope: SQLAlchemy persistence queries and FastAPI transport behavior.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime

import pytest

from modules.knowledge_graph.dto import SemanticMapProjectionNode
from modules.semantic_map.dto import SemanticMapManifest, SemanticMapRegionTile
from modules.semantic_map.geometry import build_cluster_hull
from modules.semantic_map.rebuild import SemanticMapRebuildService


@dataclass(slots=True)
class _StubProjectionPort:
    nodes: list[SemanticMapProjectionNode]

    async def list_projection_nodes_for_semantic_map(self) -> list[SemanticMapProjectionNode]:
        return self.nodes


@dataclass(slots=True)
class _RecordingSnapshotRepo:
    published_manifest: SemanticMapManifest | None = None
    published_tiles: list[SemanticMapRegionTile] | None = None

    async def publish_snapshot(
        self,
        *,
        manifest: SemanticMapManifest,
        tiles: Sequence[SemanticMapRegionTile],
    ) -> None:
        self.published_manifest = manifest
        self.published_tiles = list(tiles)


@pytest.mark.anyio
async def test_rebuild_skips_publication_when_projection_source_is_empty() -> None:
    repo = _RecordingSnapshotRepo()
    service = SemanticMapRebuildService(
        projection_port=_StubProjectionPort(nodes=[]),
        snapshot_repo=repo,
        now=lambda: datetime(2026, 4, 3, 12, 0, tzinfo=UTC),
    )

    version = await service.rebuild_current_snapshot()

    assert version is None
    assert repo.published_manifest is None
    assert repo.published_tiles is None


@pytest.mark.anyio
async def test_rebuild_creates_current_snapshot_with_region_tiles() -> None:
    repo = _RecordingSnapshotRepo()
    service = SemanticMapRebuildService(
        projection_port=_StubProjectionPort(
            nodes=[
                SemanticMapProjectionNode(
                    node_id=1,
                    title="Alpha",
                    embedding=[1.0, 0.0, 0.0],
                ),
                SemanticMapProjectionNode(
                    node_id=2,
                    title="Beta",
                    embedding=[0.9, 0.1, 0.0],
                ),
                SemanticMapProjectionNode(
                    node_id=3,
                    title="Gamma",
                    embedding=[0.0, 1.0, 0.0],
                ),
                SemanticMapProjectionNode(
                    node_id=4,
                    title="Delta",
                    embedding=[0.0, 0.9, 0.1],
                ),
            ]
        ),
        snapshot_repo=repo,
        now=lambda: datetime(2026, 4, 3, 12, 0, tzinfo=UTC),
    )

    version = await service.rebuild_current_snapshot()

    assert version == "20260403_120000_000000"
    assert repo.published_manifest is not None
    assert repo.published_manifest.version == "20260403_120000_000000"
    assert repo.published_manifest.schema_version == "20260403_120000_000000"
    assert repo.published_manifest.default_semantic_level == 0
    assert repo.published_tiles is not None
    assert len(repo.published_tiles) > 0
    assert any(tile.semantic_level == 0 for tile in repo.published_tiles)
    assert any(tile.region_count > 0 for tile in repo.published_tiles)
    assert any(tile.label_count > 0 for tile in repo.published_tiles)


def test_convex_hull_returns_polygon_for_cluster_points() -> None:
    geometry = build_cluster_hull(
        [
            (0.0, 0.0),
            (1.0, 0.0),
            (0.0, 1.0),
            (1.0, 1.0),
        ]
    )

    assert geometry.type == "polygon"
