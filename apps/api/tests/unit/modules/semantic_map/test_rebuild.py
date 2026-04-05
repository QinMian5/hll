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
from modules.taxonomy.dto import TaxonomyNodeRecord, TaxonomySemanticMapAssignment


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
    assigned_leaf_depths: list[int]
    tree_nodes: list[TaxonomyNodeRecord]
    assignments: list[TaxonomySemanticMapAssignment]

    async def list_assigned_leaf_depths_for_semantic_map(self) -> list[int]:
        return list(self.assigned_leaf_depths)

    async def list_tree_nodes_for_semantic_map(self) -> list[TaxonomyNodeRecord]:
        return list(self.tree_nodes)

    async def list_semantic_map_assignments(self) -> list[TaxonomySemanticMapAssignment]:
        return list(self.assignments)


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
    taxonomy_port = _StubTaxonomyPort(
        assigned_leaf_depths=[],
        tree_nodes=[],
        assignments=[],
    )
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

    taxonomy_nodes = [
        TaxonomyNodeRecord(id=1, parent_id=None, name="Science", depth=0, is_leaf=False),
        TaxonomyNodeRecord(id=2, parent_id=1, name="Math", depth=1, is_leaf=False),
        TaxonomyNodeRecord(id=3, parent_id=2, name="Algebra", depth=2, is_leaf=True),
        TaxonomyNodeRecord(id=4, parent_id=2, name="Geometry", depth=2, is_leaf=True),
    ]
    assignments = [
        TaxonomySemanticMapAssignment(node_id=1, taxonomy_leaf_id=3),
        TaxonomySemanticMapAssignment(node_id=2, taxonomy_leaf_id=3),
        TaxonomySemanticMapAssignment(node_id=3, taxonomy_leaf_id=4),
        TaxonomySemanticMapAssignment(node_id=4, taxonomy_leaf_id=4),
    ]
    service = SemanticMapRebuildService(
        projection_port=projection_port,
        taxonomy_port=_StubTaxonomyPort(
            assigned_leaf_depths=[2],
            tree_nodes=taxonomy_nodes,
            assignments=assignments,
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
    assert [level.level for level in repo.published_manifest.semantic_levels] == [0, 1, 2, 3]
    assert repo.published_tiles is not None
    assert len(repo.published_tiles) > 0
    assert any(tile.semantic_level == 0 for tile in repo.published_tiles)
    assert any(tile.region_count > 0 for tile in repo.published_tiles)
    assert any(tile.label_count > 0 for tile in repo.published_tiles)
    assert any(tile.points for tile in repo.published_tiles)
    region_names = {region.region_name for tile in repo.published_tiles for region in tile.regions}
    assert "Science" in region_names
    assert projection_port.requested_node_ids == [[1, 2, 3, 4]]


@pytest.mark.anyio
async def test_rebuild_skips_publication_when_leaf_depths_are_unavailable() -> None:
    repo = _RecordingSnapshotRepo()
    service = SemanticMapRebuildService(
        projection_port=_StubProjectionPort(
            nodes=[
                SemanticMapProjectionNode(
                    node_id=1,
                    title="Alpha",
                    embedding=[1.0, 0.0, 0.0],
                )
            ]
        ),
        taxonomy_port=_StubTaxonomyPort(
            assigned_leaf_depths=[],
            tree_nodes=[
                TaxonomyNodeRecord(
                    id=7,
                    parent_id=None,
                    name="Science",
                    depth=0,
                    is_leaf=True,
                )
            ],
            assignments=[TaxonomySemanticMapAssignment(node_id=1, taxonomy_leaf_id=7)],
        ),
        snapshot_repo=repo,
        now=lambda: datetime(2026, 4, 3, 12, 0, tzinfo=UTC),
    )

    version = await service.rebuild_current_snapshot()

    assert version is None
    assert repo.published_manifest is None


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
