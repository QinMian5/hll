"""
Abstract: Unit tests for semantic-map rebuild orchestration and geometry helpers.
Out of scope: SQLAlchemy persistence queries and FastAPI transport behavior.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime

import pytest

from modules.knowledge_graph.dto import SemanticMapProjectionNode
from modules.semantic_map.dto import SemanticMapManifest, SemanticMapRegionTile
from modules.semantic_map.geometry import build_cluster_hull
from modules.semantic_map.rebuild import SemanticMapRebuildService


@dataclass(slots=True)
class _StubProjectionPort:
    nodes: list[SemanticMapProjectionNode]
    requested_node_ids: list[list[int]] = field(default_factory=list)

    async def list_projection_nodes_for_semantic_map(self) -> list[SemanticMapProjectionNode]:
        return self.nodes

    async def list_projection_nodes_for_node_ids(
        self,
        *,
        node_ids: list[int],
    ) -> list[SemanticMapProjectionNode]:
        self.requested_node_ids.append(list(node_ids))
        return [node for node in self.nodes if node.node_id in node_ids]


@dataclass(slots=True)
class _StubTaxonomyPort:
    assigned_node_ids: list[int]

    async def list_assigned_node_ids_for_semantic_map(self) -> list[int]:
        return list(self.assigned_node_ids)


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
    taxonomy_port = _StubTaxonomyPort(assigned_node_ids=[])
    service = SemanticMapRebuildService(
        projection_port=_StubProjectionPort(nodes=[]),
        taxonomy_port=taxonomy_port,
        snapshot_repo=repo,
        now=lambda: datetime(2026, 4, 3, 12, 0, tzinfo=UTC),
    )

    version = await service.rebuild_current_snapshot()

    assert version is None
    assert repo.published_manifest is None
    assert repo.published_tiles is None


@pytest.mark.anyio
async def test_rebuild_creates_current_snapshot_with_region_tiles() -> None:
    projection_port = _StubProjectionPort(
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
    )
    repo = _RecordingSnapshotRepo()
    service = SemanticMapRebuildService(
        projection_port=projection_port,
        taxonomy_port=_StubTaxonomyPort(assigned_node_ids=[1, 2, 3, 4]),
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
    assert projection_port.requested_node_ids == [[1, 2, 3, 4]]


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
