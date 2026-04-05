"""
Abstract: Unit tests for the semantic-map HTTP route contract.
Out of scope: Build orchestration and SQLAlchemy persistence behavior.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import pytest
from fastapi import FastAPI
from httpx import AsyncClient

from core.errors import ApplicationError, DomainError, ErrorCode
from entrypoints.api import providers as api_providers
from modules.semantic_map.read.schema import (
    CoordinateSystemResponse,
    DefaultViewResponse,
    SemanticLevelResponse,
    SemanticMapManifestResponse,
    SemanticMapTileMetadataResponse,
    SemanticMapTileResponse,
    SemanticMapTileStatsResponse,
)

DependencyOverrides = dict[Callable[..., Any], Callable[..., Any]]


def _manifest_response() -> SemanticMapManifestResponse:
    return SemanticMapManifestResponse(
        version="20260403_120000_000000",
        schema_version="20260403_120000_000000",
        built_at=datetime(2026, 4, 3, 12, 0, tzinfo=UTC),
        coordinate_system=CoordinateSystemResponse(
            kind="cartesian2d",
            axis_direction="x-right-y-up",
            bounds_format="min_x_min_y_max_x_max_y",
        ),
        world_bounds=(0.0, 0.0, 1000.0, 1000.0),
        tile_size=512,
        max_zoom=6,
        default_view=DefaultViewResponse(target=(500.0, 500.0), zoom=0.0),
        default_semantic_level=0,
        semantic_levels=[
            SemanticLevelResponse(
                level=0,
                stable_id="domains",
                display_name="Domains",
                min_zoom=0,
                max_zoom=1,
                region_role="domain",
                child_content_role="theme",
            )
        ],
    )


def _empty_tile_response() -> SemanticMapTileResponse:
    return SemanticMapTileResponse(
        schema_version="20260403_120000_000000",
        version="20260403_120000_000000",
        semantic_level=0,
        tile=SemanticMapTileMetadataResponse(
            z=0,
            x=0,
            y=0,
            tile_bounds=(0.0, 0.0, 1000.0, 1000.0),
            bounds_format="min_x_min_y_max_x_max_y",
        ),
        stats=SemanticMapTileStatsResponse(region_count=0, label_count=0),
        regions=[],
        labels=[],
        points=[],
    )


@dataclass(slots=True)
class _FakeSemanticMapService:
    async def get_current_manifest(self) -> SemanticMapManifestResponse:
        return _manifest_response()

    async def get_region_tile(
        self,
        *,
        version: str,
        semantic_level: int,
        tile_z: int,
        tile_x: int,
        tile_y: int,
    ) -> SemanticMapTileResponse:
        assert version == "20260403_120000_000000"
        assert semantic_level == 0
        assert tile_z == 0
        assert tile_x == 0
        assert tile_y == 0
        return _empty_tile_response()


@dataclass(slots=True)
class _FakeSemanticMapNotFoundService:
    async def get_current_manifest(self) -> SemanticMapManifestResponse:
        raise DomainError(
            code=ErrorCode.DOMAIN_SEMANTIC_MAP_RESOURCE_NOT_FOUND,
            message="Semantic-map snapshot is unavailable.",
            hint="Run a semantic-map build and retry.",
        )

    async def get_region_tile(
        self,
        *,
        version: str,
        semantic_level: int,
        tile_z: int,
        tile_x: int,
        tile_y: int,
    ) -> SemanticMapTileResponse:
        raise DomainError(
            code=ErrorCode.DOMAIN_SEMANTIC_MAP_RESOURCE_NOT_FOUND,
            message="Semantic-map snapshot version was not found.",
            hint="Refresh manifest/current and retry with an available version.",
        )


@dataclass(slots=True)
class _FakeSemanticMapInputErrorService:
    async def get_current_manifest(self) -> SemanticMapManifestResponse:
        return _manifest_response()

    async def get_region_tile(
        self,
        *,
        version: str,
        semantic_level: int,
        tile_z: int,
        tile_x: int,
        tile_y: int,
    ) -> SemanticMapTileResponse:
        raise ApplicationError(
            code=ErrorCode.APPLICATION_SEMANTIC_MAP_INPUT_INVALID,
            message="Semantic-map tile request is invalid.",
            hint="Use a supported semantic level and non-negative tile coordinates.",
        )


@pytest.fixture
def dependency_overrides() -> DependencyOverrides:
    return {
        api_providers.get_semantic_map_service: lambda: _FakeSemanticMapService(),
    }


@pytest.mark.anyio
async def test_manifest_current_route_returns_expected_payload_shape(
    async_client: AsyncClient,
) -> None:
    response = await async_client.get("/semantic-map/manifest/current")

    assert response.status_code == 200
    payload = response.json()
    assert payload["version"] == "20260403_120000_000000"
    assert payload["coordinate_system"]["kind"] == "cartesian2d"
    assert payload["semantic_levels"][0]["stable_id"] == "domains"


@pytest.mark.anyio
async def test_manifest_current_returns_404_when_no_snapshot(
    async_client: AsyncClient,
    app: FastAPI,
) -> None:
    app.dependency_overrides[api_providers.get_semantic_map_service] = lambda: (
        _FakeSemanticMapNotFoundService()
    )

    response = await async_client.get("/semantic-map/manifest/current")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "DOMAIN_SEMANTIC_MAP_RESOURCE_NOT_FOUND"


@pytest.mark.anyio
async def test_region_tile_returns_empty_payload_for_empty_tile(
    async_client: AsyncClient,
) -> None:
    response = await async_client.get(
        "/semantic-map/versions/20260403_120000_000000/tiles/regions/0/0/0/0"
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["regions"] == []
    assert payload["labels"] == []
    assert payload["points"] == []
    assert payload["stats"] == {"region_count": 0, "label_count": 0}


@pytest.mark.anyio
async def test_region_tile_returns_400_for_invalid_semantic_level(
    async_client: AsyncClient,
    app: FastAPI,
) -> None:
    app.dependency_overrides[api_providers.get_semantic_map_service] = lambda: (
        _FakeSemanticMapInputErrorService()
    )

    response = await async_client.get(
        "/semantic-map/versions/20260403_120000_000000/tiles/regions/99/0/0/0"
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "APPLICATION_SEMANTIC_MAP_INPUT_INVALID"
