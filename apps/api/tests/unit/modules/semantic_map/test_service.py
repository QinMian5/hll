"""
Abstract: Unit tests for semantic-map read-service response shaping and error semantics.
Out of scope: FastAPI transport wiring and SQLAlchemy query execution.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

import pytest

from core.errors import ApplicationError, DomainError, ErrorCode
from modules.semantic_map.dto import DefaultView, SemanticMapManifest, SemanticMapRegionTile
from modules.semantic_map.schema import SemanticMapManifestResponse, SemanticMapTileResponse
from modules.semantic_map.service import SemanticMapService
from modules.semantic_map.types import LabelPayload, PolygonGeometryPayload, RegionPayload


def _build_manifest(*, version: str = "20260403_120000_000000") -> SemanticMapManifest:
    return SemanticMapManifest(
        version=version,
        schema_version=version,
        built_at=datetime(2026, 4, 3, 12, 0, tzinfo=UTC),
        world_bounds=(0.0, 0.0, 1000.0, 1000.0),
        tile_size=512,
        max_zoom=6,
        default_view=DefaultView(target=(500.0, 500.0), zoom=0.0),
        default_semantic_level=0,
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
    assert response.semantic_levels[0].stable_id == "domains"


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
    assert response.stats.region_count == 0
    assert response.stats.label_count == 0


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
        regions=[_build_region_payload()],
        labels=[_build_label_payload()],
    )
    service = SemanticMapService(
        repo=_StubRepo(version_manifest=manifest, tile=tile),
    )

    response = await service.get_region_tile(
        version=manifest.version,
        semantic_level=0,
        tile_z=0,
        tile_x=0,
        tile_y=0,
    )

    assert response.regions[0].region_name == "Alpha · Beta"
    assert response.labels[0].text == "Alpha"
