"""
Abstract: Unit tests for taxonomy view HTTP route contracts and payload shapes.
Out of scope: Taxonomy repository SQL behavior and classification orchestration.
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
from modules.taxonomy.schema import (
    TaxonomyLeafLayoutNodeResponse,
    TaxonomyLeafLayoutSliceResponse,
    TaxonomyLeafNodeDetailResponse,
    TaxonomyLeafNodeDetailsResponse,
    TaxonomyLeafNodeTitleResponse,
    TaxonomyLeafNodeTitlesResponse,
    TaxonomyLeafWorldBoundsResponse,
    TaxonomyNodeBranchViewResponse,
    TaxonomyNodeLeafViewResponse,
    TaxonomyRootViewResponse,
    TaxonomyViewChildResponse,
    TaxonomyViewNodeResponse,
)

DependencyOverrides = dict[Callable[..., Any], Callable[..., Any]]


@dataclass(slots=True)
class _FakeTaxonomyService:
    async def get_root_view(self) -> TaxonomyRootViewResponse:
        return TaxonomyRootViewResponse(
            breadcrumb=[],
            children=[
                TaxonomyViewChildResponse(
                    id=1,
                    parent_id=None,
                    name="Science",
                    route_slug="science",
                    route_path="science",
                    depth=0,
                    is_leaf=False,
                    descendant_card_count=12,
                )
            ],
        )

    async def get_node_view(
        self,
        *,
        node_id: int,
    ) -> TaxonomyNodeBranchViewResponse | TaxonomyNodeLeafViewResponse:
        if node_id == 1:
            return TaxonomyNodeBranchViewResponse(
                node_kind="branch",
                current_node=TaxonomyViewNodeResponse(
                    id=1,
                    parent_id=None,
                    name="Science",
                    route_slug="science",
                    route_path="science",
                    depth=0,
                    is_leaf=False,
                ),
                breadcrumb=[
                    TaxonomyViewNodeResponse(
                        id=1,
                        parent_id=None,
                        name="Science",
                        route_slug="science",
                        route_path="science",
                        depth=0,
                        is_leaf=False,
                    )
                ],
                children=[
                    TaxonomyViewChildResponse(
                        id=2,
                        parent_id=1,
                        name="Mathematics",
                        route_slug="mathematics",
                        route_path="science/mathematics",
                        depth=1,
                        is_leaf=True,
                        descendant_card_count=3,
                    )
                ],
            )
        return TaxonomyNodeLeafViewResponse(
            node_kind="leaf",
            current_node=TaxonomyViewNodeResponse(
                id=node_id,
                parent_id=1,
                name="Mathematics",
                route_slug="mathematics",
                route_path="science/mathematics",
                depth=1,
                is_leaf=True,
            ),
            breadcrumb=[
                TaxonomyViewNodeResponse(
                    id=1,
                    parent_id=None,
                    name="Science",
                    route_slug="science",
                    route_path="science",
                    depth=0,
                    is_leaf=False,
                ),
                TaxonomyViewNodeResponse(
                    id=node_id,
                    parent_id=1,
                    name="Mathematics",
                    route_slug="mathematics",
                    route_path="science/mathematics",
                    depth=1,
                    is_leaf=True,
                ),
            ],
            layout_version="taxonomy-leaf-layout-v3",
            world_bounds=TaxonomyLeafWorldBoundsResponse(
                min_x=0.0,
                min_y=0.0,
                max_x=0.0,
                max_y=0.0,
            ),
            node_count=3,
            edge_count=2,
            generated_at=datetime(2026, 4, 29, 12, 0, tzinfo=UTC),
        )

    async def get_node_view_by_route_path(
        self,
        *,
        route_path: str,
    ) -> TaxonomyNodeBranchViewResponse | TaxonomyNodeLeafViewResponse:
        assert route_path == "science/mathematics"
        return await self.get_node_view(node_id=2)

    async def get_leaf_layout_slice(
        self,
        *,
        node_id: int,
        min_x: float,
        min_y: float,
        max_x: float,
        max_y: float,
    ) -> TaxonomyLeafLayoutSliceResponse:
        assert node_id == 2
        assert (min_x, min_y, max_x, max_y) == (-10.0, -20.0, 30.0, 40.0)
        return TaxonomyLeafLayoutSliceResponse(
            leaf_id=2,
            layout_version="taxonomy-leaf-layout-v3",
            requested_bounds=TaxonomyLeafWorldBoundsResponse(
                min_x=-10.0,
                min_y=-20.0,
                max_x=30.0,
                max_y=40.0,
            ),
            nodes=[
                TaxonomyLeafLayoutNodeResponse(
                    id=11,
                    scope="inner",
                    x=1.5,
                    y=2.5,
                )
            ],
            edges=[],
        )

    async def get_leaf_node_details(
        self,
        *,
        node_id: int,
        node_ids: list[int],
    ) -> TaxonomyLeafNodeDetailsResponse:
        assert node_id == 2
        assert node_ids == [11, 77]
        return TaxonomyLeafNodeDetailsResponse(
            nodes=[
                TaxonomyLeafNodeDetailResponse(
                    id=11,
                    current_version=3,
                    title="Inner 11",
                    content="Inner 11 content",
                ),
                TaxonomyLeafNodeDetailResponse(
                    id=77,
                    current_version=7,
                    title="Outer 77",
                    content="Outer 77 content",
                ),
            ]
        )

    async def get_leaf_node_titles(
        self,
        *,
        node_id: int,
        node_ids: list[int],
    ) -> TaxonomyLeafNodeTitlesResponse:
        assert node_id == 2
        assert node_ids == [11, 77]
        return TaxonomyLeafNodeTitlesResponse(
            nodes=[
                TaxonomyLeafNodeTitleResponse(
                    id=11,
                    title="Inner 11",
                ),
                TaxonomyLeafNodeTitleResponse(
                    id=77,
                    title="Outer 77",
                ),
            ]
        )


@dataclass(slots=True)
class _FakeTaxonomyNotFoundService:
    async def get_root_view(self) -> TaxonomyRootViewResponse:
        raise DomainError(
            code=ErrorCode.DOMAIN_TAXONOMY_RESOURCE_NOT_FOUND,
            message="Taxonomy tree is not available.",
            hint="Import taxonomy data and retry.",
        )

    async def get_node_view(
        self,
        *,
        node_id: int,
    ) -> TaxonomyNodeBranchViewResponse | TaxonomyNodeLeafViewResponse:
        raise DomainError(
            code=ErrorCode.DOMAIN_TAXONOMY_RESOURCE_NOT_FOUND,
            message=f"Taxonomy node {node_id} was not found.",
            hint="Use an existing taxonomy node id and retry.",
        )

    async def get_node_view_by_route_path(
        self,
        *,
        route_path: str,
    ) -> TaxonomyNodeBranchViewResponse | TaxonomyNodeLeafViewResponse:
        raise DomainError(
            code=ErrorCode.DOMAIN_TAXONOMY_RESOURCE_NOT_FOUND,
            message=f"Taxonomy route path {route_path!r} was not found.",
            hint="Use an existing taxonomy route path and retry.",
        )

    async def get_leaf_node_details(
        self,
        *,
        node_id: int,
        node_ids: list[int],
    ) -> TaxonomyLeafNodeDetailsResponse:
        raise DomainError(
            code=ErrorCode.DOMAIN_TAXONOMY_RESOURCE_NOT_FOUND,
            message=f"Taxonomy node {node_id} was not found.",
            hint="Use an existing taxonomy node id and retry.",
        )

    async def get_leaf_layout_slice(
        self,
        *,
        node_id: int,
        min_x: float,
        min_y: float,
        max_x: float,
        max_y: float,
    ) -> TaxonomyLeafLayoutSliceResponse:
        raise DomainError(
            code=ErrorCode.DOMAIN_TAXONOMY_RESOURCE_NOT_FOUND,
            message=f"Taxonomy node {node_id} was not found.",
            hint="Use an existing taxonomy node id and retry.",
        )

    async def get_leaf_node_titles(
        self,
        *,
        node_id: int,
        node_ids: list[int],
    ) -> TaxonomyLeafNodeTitlesResponse:
        raise DomainError(
            code=ErrorCode.DOMAIN_TAXONOMY_RESOURCE_NOT_FOUND,
            message=f"Taxonomy node {node_id} was not found.",
            hint="Use an existing taxonomy node id and retry.",
        )


@dataclass(slots=True)
class _FakeTaxonomyInvalidDetailsService:
    async def get_root_view(self) -> TaxonomyRootViewResponse:
        raise NotImplementedError

    async def get_node_view(
        self,
        *,
        node_id: int,
    ) -> TaxonomyNodeBranchViewResponse | TaxonomyNodeLeafViewResponse:
        raise NotImplementedError

    async def get_leaf_node_details(
        self,
        *,
        node_id: int,
        node_ids: list[int],
    ) -> TaxonomyLeafNodeDetailsResponse:
        message = "Leaf detail request is invalid."
        if not node_ids:
            message = "Leaf detail request requires at least one node id."
        elif len(node_ids) != len(set(node_ids)):
            message = "Leaf detail request contains duplicate node ids."
        elif node_id == 1:
            message = "Leaf detail request requires a leaf taxonomy node."
        else:
            message = "Leaf detail request references nodes outside the active leaf graph."
        raise ApplicationError(
            code=ErrorCode.APPLICATION_TAXONOMY_INPUT_INVALID,
            message=message,
            hint="Send only unique node ids from the active leaf graph and retry.",
        )

    async def get_leaf_node_titles(
        self,
        *,
        node_id: int,
        node_ids: list[int],
    ) -> TaxonomyLeafNodeTitlesResponse:
        message = "Leaf title request is invalid."
        if not node_ids:
            message = "Leaf title request requires at least one node id."
        elif len(node_ids) != len(set(node_ids)):
            message = "Leaf title request contains duplicate node ids."
        elif node_id == 1:
            message = "Leaf title request requires a leaf taxonomy node."
        else:
            message = "Leaf title request references nodes outside the active leaf graph."
        raise ApplicationError(
            code=ErrorCode.APPLICATION_TAXONOMY_INPUT_INVALID,
            message=message,
            hint="Send only unique node ids from the active leaf graph and retry.",
        )


@pytest.fixture
def dependency_overrides() -> DependencyOverrides:
    return {
        api_providers.get_taxonomy_service: lambda: _FakeTaxonomyService(),
    }


@pytest.mark.anyio
async def test_root_view_route_returns_top_level_children(
    async_client: AsyncClient,
) -> None:
    response = await async_client.get("/api/v1/taxonomy/view/root")

    assert response.status_code == 200
    payload = response.json()
    assert payload["breadcrumb"] == []
    assert payload["children"] == [
        {
            "id": 1,
            "parent_id": None,
            "name": "Science",
            "route_slug": "science",
            "route_path": "science",
            "depth": 0,
            "is_leaf": False,
            "descendant_card_count": 12,
        }
    ]


@pytest.mark.anyio
async def test_node_view_route_returns_branch_payload_for_non_leaf(
    async_client: AsyncClient,
) -> None:
    response = await async_client.get("/api/v1/taxonomy/view/nodes/1")

    assert response.status_code == 200
    payload = response.json()
    assert payload["node_kind"] == "branch"
    assert payload["current_node"] == {
        "id": 1,
        "parent_id": None,
        "name": "Science",
        "route_slug": "science",
        "route_path": "science",
        "depth": 0,
        "is_leaf": False,
    }
    assert payload["children"][0] == {
        "id": 2,
        "parent_id": 1,
        "name": "Mathematics",
        "route_slug": "mathematics",
        "route_path": "science/mathematics",
        "depth": 1,
        "is_leaf": True,
        "descendant_card_count": 3,
    }


@pytest.mark.anyio
async def test_path_view_route_returns_node_payload_for_canonical_route_path(
    async_client: AsyncClient,
) -> None:
    response = await async_client.get("/api/v1/taxonomy/view/path/science/mathematics")

    assert response.status_code == 200
    payload = response.json()
    assert payload["node_kind"] == "leaf"
    assert payload["current_node"]["id"] == 2
    assert payload["current_node"]["route_path"] == "science/mathematics"


@pytest.mark.anyio
async def test_node_view_route_returns_leaf_payload_for_leaf(
    async_client: AsyncClient,
) -> None:
    response = await async_client.get("/api/v1/taxonomy/view/nodes/2")

    assert response.status_code == 200
    payload = response.json()
    assert payload["node_kind"] == "leaf"
    assert payload["current_node"]["id"] == 2
    assert payload["current_node"]["route_path"] == "science/mathematics"
    assert payload["layout_version"] == "taxonomy-leaf-layout-v3"
    assert payload["world_bounds"] == {
        "min_x": 0.0,
        "min_y": 0.0,
        "max_x": 0.0,
        "max_y": 0.0,
    }
    assert payload["node_count"] == 3
    assert payload["edge_count"] == 2
    assert payload["generated_at"] == "2026-04-29T12:00:00Z"


@pytest.mark.anyio
async def test_leaf_layout_route_returns_requested_layout_slice(
    async_client: AsyncClient,
) -> None:
    response = await async_client.get(
        "/api/v1/taxonomy/view/leaves/2/layout",
        params={
            "min_x": -10.0,
            "min_y": -20.0,
            "max_x": 30.0,
            "max_y": 40.0,
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "leaf_id": 2,
        "layout_version": "taxonomy-leaf-layout-v3",
        "requested_bounds": {
            "min_x": -10.0,
            "min_y": -20.0,
            "max_x": 30.0,
            "max_y": 40.0,
        },
        "nodes": [
            {
                "id": 11,
                "scope": "inner",
                "x": 1.5,
                "y": 2.5,
            }
        ],
        "edges": [],
    }


@pytest.mark.anyio
async def test_leaf_details_route_returns_ordered_detail_records(
    async_client: AsyncClient,
) -> None:
    response = await async_client.post(
        "/api/v1/taxonomy/view/leaves/2/details",
        json={"node_ids": [11, 77]},
    )

    assert response.status_code == 200
    assert response.json() == {
        "nodes": [
            {
                "id": 11,
                "current_version": 3,
                "title": "Inner 11",
                "content": "Inner 11 content",
            },
            {
                "id": 77,
                "current_version": 7,
                "title": "Outer 77",
                "content": "Outer 77 content",
            },
        ]
    }


@pytest.mark.anyio
async def test_leaf_titles_route_returns_ordered_title_records(
    async_client: AsyncClient,
) -> None:
    response = await async_client.post(
        "/api/v1/taxonomy/view/leaves/2/titles",
        json={"node_ids": [11, 77]},
    )

    assert response.status_code == 200
    assert response.json() == {
        "nodes": [
            {
                "id": 11,
                "title": "Inner 11",
            },
            {
                "id": 77,
                "title": "Outer 77",
            },
        ]
    }


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("payload", "leaf_id", "expected_message"),
    [
        ({"node_ids": []}, 2, "at least one node id"),
        ({"node_ids": [11, 11]}, 2, "duplicate node ids"),
        ({"node_ids": [11]}, 1, "requires a leaf taxonomy node"),
        ({"node_ids": [999]}, 2, "outside the active leaf graph"),
    ],
)
async def test_leaf_details_route_returns_400_for_invalid_detail_requests(
    async_client: AsyncClient,
    app: FastAPI,
    payload: dict[str, list[int]],
    leaf_id: int,
    expected_message: str,
) -> None:
    app.dependency_overrides[api_providers.get_taxonomy_service] = lambda: (
        _FakeTaxonomyInvalidDetailsService()
    )

    response = await async_client.post(
        f"/api/v1/taxonomy/view/leaves/{leaf_id}/details",
        json=payload,
    )

    assert response.status_code == 400
    error = response.json()["error"]
    assert error["code"] == "APPLICATION_TAXONOMY_INPUT_INVALID"
    assert expected_message in error["message"]


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("payload", "leaf_id", "expected_message"),
    [
        ({"node_ids": []}, 2, "at least one node id"),
        ({"node_ids": [11, 11]}, 2, "duplicate node ids"),
        ({"node_ids": [11]}, 1, "requires a leaf taxonomy node"),
        ({"node_ids": [999]}, 2, "outside the active leaf graph"),
    ],
)
async def test_leaf_titles_route_returns_400_for_invalid_title_requests(
    async_client: AsyncClient,
    app: FastAPI,
    payload: dict[str, list[int]],
    leaf_id: int,
    expected_message: str,
) -> None:
    app.dependency_overrides[api_providers.get_taxonomy_service] = lambda: (
        _FakeTaxonomyInvalidDetailsService()
    )

    response = await async_client.post(
        f"/api/v1/taxonomy/view/leaves/{leaf_id}/titles",
        json=payload,
    )

    assert response.status_code == 400
    error = response.json()["error"]
    assert error["code"] == "APPLICATION_TAXONOMY_INPUT_INVALID"
    assert expected_message in error["message"]


@pytest.mark.anyio
async def test_taxonomy_view_routes_return_404_when_taxonomy_unavailable(
    async_client: AsyncClient,
    app: FastAPI,
) -> None:
    app.dependency_overrides[api_providers.get_taxonomy_service] = lambda: (
        _FakeTaxonomyNotFoundService()
    )

    root_response = await async_client.get("/api/v1/taxonomy/view/root")
    node_response = await async_client.get("/api/v1/taxonomy/view/nodes/123")
    path_response = await async_client.get("/api/v1/taxonomy/view/path/science/missing")

    assert root_response.status_code == 404
    assert node_response.status_code == 404
    assert path_response.status_code == 404
    assert root_response.json()["error"]["code"] == "DOMAIN_TAXONOMY_RESOURCE_NOT_FOUND"
    assert node_response.json()["error"]["code"] == "DOMAIN_TAXONOMY_RESOURCE_NOT_FOUND"
    assert path_response.json()["error"]["code"] == "DOMAIN_TAXONOMY_RESOURCE_NOT_FOUND"
