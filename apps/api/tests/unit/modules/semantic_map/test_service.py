"""
Abstract: Unit tests for semantic-map read-service response shaping and error semantics.
Out of scope: FastAPI transport wiring and SQLAlchemy query execution.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

import pytest

from core.errors import ApplicationError, DomainError, ErrorCode
from modules.semantic_map.core.dto import DefaultView, SemanticMapManifest, SemanticMapRegionTile
from modules.semantic_map.core.types import (
    EdgePayload,
    LabelPayload,
    PointPayload,
    PolygonGeometryPayload,
    RegionPayload,
)
from modules.semantic_map.metadata import (
    SemanticLevelDefinition,
    build_semantic_levels_from_leaf_depths,
)
from modules.semantic_map.read.schema import SemanticMapManifestResponse, SemanticMapTileResponse
from modules.semantic_map.read.service import SemanticMapService


def _build_manifest(
    *,
    version: str = "20260403_120000_000000",
    semantic_levels: list[SemanticLevelDefinition] | None = None,
) -> SemanticMapManifest:
    return SemanticMapManifest(
        version=version,
        schema_version=version,
        built_at=datetime(2026, 4, 3, 12, 0, tzinfo=UTC),
        world_bounds=(0.0, 0.0, 1000.0, 1000.0),
        tile_size=512,
        max_zoom=6,
        default_view=DefaultView(target=(500.0, 500.0), zoom=0.0),
        default_semantic_level=0,
        semantic_levels=(
            semantic_levels
            if semantic_levels is not None
            else list(build_semantic_levels_from_leaf_depths(leaf_depths=[2]))
        ),
    )


def _build_region_payload() -> RegionPayload:
    return RegionPayload(
        id="domains:1",
        parent_id=None,
        region_name="Alpha · Beta",
        centroid=[500.0, 500.0],
        bbox=[400.0, 400.0, 600.0, 600.0],
        geometry=PolygonGeometryPayload(
            type="polygon",
            coordinates=[
                [400.0, 400.0],
                [600.0, 400.0],
                [600.0, 600.0],
                [400.0, 600.0],
                [400.0, 400.0],
            ],
        ),
        display_rank=1,
        children_available=True,
    )


def _build_label_payload() -> LabelPayload:
    return LabelPayload(
        id="domains:1:label:1",
        region_id="domains:1",
        text="Alpha",
        position=[500.0, 500.0],
        label_rank=1,
        font_size=22,
    )


def _build_point_payload() -> PointPayload:
    return PointPayload(
        id="card:1",
        node_id=1,
        leaf_region_id="taxonomy:9",
        title="Alpha",
        position=[500.0, 500.0],
    )


def _build_edge_payload() -> EdgePayload:
    return EdgePayload(
        id="edge:1:2",
        source_node_id=1,
        target_node_id=2,
        strength=0.87,
        source_position=[500.0, 500.0],
        target_position=[540.0, 500.0],
    )


@dataclass(slots=True)
class _StubRepo:
    current_manifest: SemanticMapManifest | None = None
    version_manifest: SemanticMapManifest | None = None
    tile: SemanticMapRegionTile | None = None
    requested_version: str | None = None

    async def get_current_manifest(self) -> SemanticMapManifest | None:
        return self.current_manifest

    async def get_manifest_by_version(self, *, version: str) -> SemanticMapManifest | None:
        self.requested_version = version
        return self.version_manifest

    async def get_region_tile(
        self,
        *,
        version: str,
        semantic_level: int,
        tile_z: int,
        tile_x: int,
        tile_y: int,
    ) -> SemanticMapRegionTile | None:
        self.requested_version = version
        return self.tile


@pytest.mark.anyio
async def test_get_current_manifest_returns_transport_response() -> None:
    service = SemanticMapService(repo=_StubRepo(current_manifest=_build_manifest()))

    response = await service.get_current_manifest()

    assert isinstance(response, SemanticMapManifestResponse)
    assert response.version == "20260403_120000_000000"
    assert response.coordinate_system.kind == "cartesian2d"
    assert [level.level for level in response.semantic_levels] == [0, 1, 2, 3]
    assert response.semantic_levels[0].stable_id == "taxonomy_depth_0"
    assert response.semantic_levels[-1].stable_id == "cards"


@pytest.mark.anyio
async def test_get_current_manifest_raises_not_found_when_snapshot_missing() -> None:
    service = SemanticMapService(repo=_StubRepo())

    with pytest.raises(DomainError) as exc_info:
        await service.get_current_manifest()

    assert exc_info.value.code == ErrorCode.DOMAIN_SEMANTIC_MAP_RESOURCE_NOT_FOUND


@pytest.mark.anyio
async def test_get_region_tile_returns_empty_payload_for_known_snapshot_without_tile() -> None:
    manifest = _build_manifest(version="20260403_153000_000000")
    service = SemanticMapService(repo=_StubRepo(version_manifest=manifest))

    response = await service.get_region_tile(
        version="20260403_153000_000000",
        semantic_level=0,
        tile_z=0,
        tile_x=0,
        tile_y=0,
    )

    assert isinstance(response, SemanticMapTileResponse)
    assert response.version == "20260403_153000_000000"
    assert response.regions == []
    assert response.labels == []
    assert response.points == []
    assert response.stats.region_count == 0
    assert response.stats.label_count == 0
    assert response.stats.edge_count == 0


@pytest.mark.anyio
async def test_get_region_tile_raises_not_found_for_unknown_version() -> None:
    service = SemanticMapService(repo=_StubRepo())

    with pytest.raises(DomainError) as exc_info:
        await service.get_region_tile(
            version="20260403_153000_000000",
            semantic_level=0,
            tile_z=0,
            tile_x=0,
            tile_y=0,
        )

    assert exc_info.value.code == ErrorCode.DOMAIN_SEMANTIC_MAP_RESOURCE_NOT_FOUND


@pytest.mark.anyio
async def test_get_region_tile_raises_input_invalid_for_unknown_semantic_level() -> None:
    manifest = _build_manifest()
    service = SemanticMapService(repo=_StubRepo(version_manifest=manifest))

    with pytest.raises(ApplicationError) as exc_info:
        await service.get_region_tile(
            version=manifest.version,
            semantic_level=99,
            tile_z=0,
            tile_x=0,
            tile_y=0,
        )

    assert exc_info.value.code == ErrorCode.APPLICATION_SEMANTIC_MAP_INPUT_INVALID


@pytest.mark.anyio
async def test_get_region_tile_returns_transport_payload_for_materialized_tile() -> None:
    manifest = _build_manifest()
    tile = SemanticMapRegionTile(
        semantic_level=0,
        tile_z=0,
        tile_x=0,
        tile_y=0,
        tile_bounds=(0.0, 0.0, 1000.0, 1000.0),
        region_count=1,
        label_count=1,
        edge_count=1,
        regions=[_build_region_payload()],
        labels=[_build_label_payload()],
        points=[_build_point_payload()],
        edges=[_build_edge_payload()],
    )
    service = SemanticMapService(repo=_StubRepo(version_manifest=manifest, tile=tile))

    response = await service.get_region_tile(
        version=manifest.version,
        semantic_level=0,
        tile_z=0,
        tile_x=0,
        tile_y=0,
    )

    assert response.regions[0].region_name == "Alpha · Beta"
    assert response.labels[0].text == "Alpha"
    assert response.points[0].title == "Alpha"
    assert response.edges[0].id == "edge:1:2"


@pytest.mark.anyio
async def test_get_current_manifest_uses_snapshot_semantic_levels() -> None:
    semantic_levels = list(build_semantic_levels_from_leaf_depths(leaf_depths=[1, 3]))
    service = SemanticMapService(
        repo=_StubRepo(current_manifest=_build_manifest(semantic_levels=semantic_levels))
    )

    response = await service.get_current_manifest()

    assert [level.level for level in response.semantic_levels] == [0, 1, 2, 3, 4]
    assert response.semantic_levels[-1].stable_id == "cards"
    assert response.semantic_levels[-1].child_content_role == "card"


@pytest.mark.anyio
async def test_get_region_tile_accepts_terminal_card_layer_level_from_snapshot() -> None:
    semantic_levels = list(build_semantic_levels_from_leaf_depths(leaf_depths=[1, 3]))
    manifest = _build_manifest(semantic_levels=semantic_levels)
    service = SemanticMapService(repo=_StubRepo(version_manifest=manifest))

    response = await service.get_region_tile(
        version=manifest.version,
        semantic_level=4,
        tile_z=0,
        tile_x=0,
        tile_y=0,
    )

    assert isinstance(response, SemanticMapTileResponse)
    assert response.semantic_level == 4
