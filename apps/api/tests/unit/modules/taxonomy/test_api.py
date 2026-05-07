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
from modules.taxonomy.repo import TAXONOMY_NODE_SCOPE_KIND
from modules.taxonomy.schema import (
    TaxonomyCardScopeLayoutNodeResponse,
    TaxonomyCardScopeLayoutSliceResponse,
    TaxonomyCardScopeNodeDetailResponse,
    TaxonomyCardScopeNodeDetailsResponse,
    TaxonomyCardScopeNodeTitleResponse,
    TaxonomyCardScopeNodeTitlesResponse,
    TaxonomyCardScopeWorldBoundsResponse,
    TaxonomyNodeBranchViewResponse,
    TaxonomyNodeCardScopeViewResponse,
    TaxonomyRootViewResponse,
    TaxonomyViewChildResponse,
    TaxonomyViewScopeResponse,
)

DependencyOverrides = dict[Callable[..., Any], Callable[..., Any]]


def _scope(
    *,
    scope_kind: str = TAXONOMY_NODE_SCOPE_KIND,
    taxonomy_node_id: int | None = 2,
    parent_taxonomy_node_id: int | None = 1,
    name: str = "Mathematics",
    route_slug: str = "mathematics",
    route_path: str = "science/mathematics",
    depth: int = 1,
) -> TaxonomyViewScopeResponse:
    return TaxonomyViewScopeResponse(
        scope_kind=scope_kind,
        taxonomy_node_id=taxonomy_node_id,
        parent_taxonomy_node_id=parent_taxonomy_node_id,
        name=name,
        route_slug=route_slug,
        route_path=route_path,
        depth=depth,
    )


@dataclass(slots=True)
class _FakeTaxonomyService:
    async def get_root_view(self) -> TaxonomyRootViewResponse:
        return TaxonomyRootViewResponse(
            breadcrumb=[],
            children=[
                TaxonomyViewChildResponse(
                    scope_kind=TAXONOMY_NODE_SCOPE_KIND,
                    taxonomy_node_id=1,
                    parent_taxonomy_node_id=None,
                    name="Science",
                    route_slug="science",
                    route_path="science",
                    depth=0,
                    node_kind="branch",
                    descendant_card_count=12,
                )
            ],
        )

    async def get_node_view(
        self,
        *,
        node_id: int,
    ) -> TaxonomyNodeBranchViewResponse | TaxonomyNodeCardScopeViewResponse:
        if node_id == 1:
            return TaxonomyNodeBranchViewResponse(
                node_kind="branch",
                current_scope=_scope(
                    taxonomy_node_id=1,
                    parent_taxonomy_node_id=None,
                    name="Science",
                    route_slug="science",
                    route_path="science",
                    depth=0,
                ),
                breadcrumb=[
                    _scope(
                        taxonomy_node_id=1,
                        parent_taxonomy_node_id=None,
                        name="Science",
                        route_slug="science",
                        route_path="science",
                        depth=0,
                    )
                ],
                children=[
                    TaxonomyViewChildResponse(
                        scope_kind=TAXONOMY_NODE_SCOPE_KIND,
                        taxonomy_node_id=2,
                        parent_taxonomy_node_id=1,
                        name="Mathematics",
                        route_slug="mathematics",
                        route_path="science/mathematics",
                        depth=1,
                        node_kind="card_scope",
                        descendant_card_count=3,
                    )
                ],
            )
        return TaxonomyNodeCardScopeViewResponse(
            node_kind="card_scope",
            current_scope=_scope(),
            breadcrumb=[
                _scope(
                    taxonomy_node_id=1,
                    parent_taxonomy_node_id=None,
                    name="Science",
                    route_slug="science",
                    route_path="science",
                    depth=0,
                ),
                _scope(),
            ],
            layout_version="taxonomy-card-scope-layout-v2",
            layout_status="ready",
            world_bounds=TaxonomyCardScopeWorldBoundsResponse(
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
    ) -> TaxonomyNodeBranchViewResponse | TaxonomyNodeCardScopeViewResponse:
        assert route_path == "science/mathematics"
        return await self.get_node_view(node_id=2)

    async def get_card_scope_layout_slice(
        self,
        *,
        route_path: str,
        min_x: float,
        min_y: float,
        max_x: float,
        max_y: float,
    ) -> TaxonomyCardScopeLayoutSliceResponse:
        assert route_path == "science/mathematics"
        assert (min_x, min_y, max_x, max_y) == (-10.0, -20.0, 30.0, 40.0)
        return TaxonomyCardScopeLayoutSliceResponse(
            scope_kind=TAXONOMY_NODE_SCOPE_KIND,
            taxonomy_node_id=2,
            parent_taxonomy_node_id=1,
            route_path=route_path,
            layout_version="taxonomy-card-scope-layout-v2",
            layout_status="ready",
            requested_bounds=TaxonomyCardScopeWorldBoundsResponse(
                min_x=-10.0,
                min_y=-20.0,
                max_x=30.0,
                max_y=40.0,
            ),
            nodes=[
                TaxonomyCardScopeLayoutNodeResponse(
                    id=11,
                    scope="inner",
                    x=1.5,
                    y=2.5,
                )
            ],
            edges=[],
        )

    async def get_card_scope_node_details(
        self,
        *,
        route_path: str,
        node_ids: list[int],
    ) -> TaxonomyCardScopeNodeDetailsResponse:
        assert route_path == "science/mathematics"
        assert node_ids == [11, 77]
        return TaxonomyCardScopeNodeDetailsResponse(
            nodes=[
                TaxonomyCardScopeNodeDetailResponse(
                    id=11,
                    current_version=3,
                    title="Inner 11",
                    content="Inner 11 content",
                ),
                TaxonomyCardScopeNodeDetailResponse(
                    id=77,
                    current_version=7,
                    title="Outer 77",
                    content="Outer 77 content",
                ),
            ]
        )

    async def get_card_scope_node_titles(
        self,
        *,
        route_path: str,
        node_ids: list[int],
    ) -> TaxonomyCardScopeNodeTitlesResponse:
        assert route_path == "science/mathematics"
        assert node_ids == [11, 77]
        return TaxonomyCardScopeNodeTitlesResponse(
            nodes=[
                TaxonomyCardScopeNodeTitleResponse(id=11, title="Inner 11"),
                TaxonomyCardScopeNodeTitleResponse(id=77, title="Outer 77"),
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

    async def get_node_view(self, *, node_id: int) -> TaxonomyNodeCardScopeViewResponse:
        raise DomainError(
            code=ErrorCode.DOMAIN_TAXONOMY_RESOURCE_NOT_FOUND,
            message=f"Taxonomy node {node_id} was not found.",
            hint="Use an existing taxonomy node id and retry.",
        )

    async def get_node_view_by_route_path(
        self,
        *,
        route_path: str,
    ) -> TaxonomyNodeCardScopeViewResponse:
        raise DomainError(
            code=ErrorCode.DOMAIN_TAXONOMY_RESOURCE_NOT_FOUND,
            message=f"Taxonomy route path {route_path!r} was not found.",
            hint="Use an existing taxonomy route path and retry.",
        )


@dataclass(slots=True)
class _FakeTaxonomyInvalidDetailsService:
    async def get_card_scope_node_details(
        self,
        *,
        route_path: str,
        node_ids: list[int],
    ) -> TaxonomyCardScopeNodeDetailsResponse:
        raise _invalid_detail_error(node_ids=node_ids, route_path=route_path)

    async def get_card_scope_node_titles(
        self,
        *,
        route_path: str,
        node_ids: list[int],
    ) -> TaxonomyCardScopeNodeTitlesResponse:
        raise _invalid_detail_error(node_ids=node_ids, route_path=route_path)


@dataclass(slots=True)
class _FakeTaxonomyLayoutNotReadyService:
    async def get_root_view(self) -> TaxonomyRootViewResponse:
        raise NotImplementedError

    async def get_node_view(self, *, node_id: int) -> TaxonomyNodeCardScopeViewResponse:
        raise _layout_not_ready_error()

    async def get_node_view_by_route_path(
        self,
        *,
        route_path: str,
    ) -> TaxonomyNodeCardScopeViewResponse:
        assert route_path == "science/mathematics"
        raise _layout_not_ready_error()

    async def get_card_scope_layout_slice(
        self,
        *,
        route_path: str,
        min_x: float,
        min_y: float,
        max_x: float,
        max_y: float,
    ) -> TaxonomyCardScopeLayoutSliceResponse:
        raise _layout_not_ready_error()


@pytest.fixture
def dependency_overrides() -> DependencyOverrides:
    return {
        api_providers.get_taxonomy_service: lambda: _FakeTaxonomyService(),
    }


@pytest.mark.anyio
async def test_root_view_route_returns_top_level_children(async_client: AsyncClient) -> None:
    response = await async_client.get("/api/v1/taxonomy/view/root")

    assert response.status_code == 200
    assert response.json()["children"] == [
        {
            "scope_kind": "taxonomy_node",
            "taxonomy_node_id": 1,
            "parent_taxonomy_node_id": None,
            "name": "Science",
            "route_slug": "science",
            "route_path": "science",
            "depth": 0,
            "node_kind": "branch",
            "descendant_card_count": 12,
        }
    ]


@pytest.mark.anyio
async def test_node_view_route_returns_branch_payload(async_client: AsyncClient) -> None:
    response = await async_client.get("/api/v1/taxonomy/view/nodes/1")

    assert response.status_code == 200
    payload = response.json()
    assert payload["node_kind"] == "branch"
    assert payload["current_scope"]["taxonomy_node_id"] == 1
    assert payload["children"][0]["node_kind"] == "card_scope"


@pytest.mark.anyio
async def test_path_view_route_returns_card_scope_payload(async_client: AsyncClient) -> None:
    response = await async_client.get("/api/v1/taxonomy/view/path/science/mathematics")

    assert response.status_code == 200
    payload = response.json()
    assert payload["node_kind"] == "card_scope"
    assert payload["current_scope"]["taxonomy_node_id"] == 2
    assert payload["current_scope"]["route_path"] == "science/mathematics"


@pytest.mark.anyio
async def test_node_view_route_returns_card_scope_payload(async_client: AsyncClient) -> None:
    response = await async_client.get("/api/v1/taxonomy/view/nodes/2")

    assert response.status_code == 200
    payload = response.json()
    assert payload["node_kind"] == "card_scope"
    assert payload["layout_version"] == "taxonomy-card-scope-layout-v2"
    assert payload["layout_status"] == "ready"
    assert payload["node_count"] == 3
    assert payload["edge_count"] == 2
    assert payload["generated_at"] == "2026-04-29T12:00:00Z"


@pytest.mark.anyio
async def test_card_scope_layout_route_returns_requested_layout_slice(
    async_client: AsyncClient,
) -> None:
    response = await async_client.get(
        "/api/v1/taxonomy/view/card-scopes/layout",
        params={
            "route_path": "science/mathematics",
            "min_x": -10.0,
            "min_y": -20.0,
            "max_x": 30.0,
            "max_y": 40.0,
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "scope_kind": "taxonomy_node",
        "taxonomy_node_id": 2,
        "parent_taxonomy_node_id": 1,
        "route_path": "science/mathematics",
        "layout_version": "taxonomy-card-scope-layout-v2",
        "layout_status": "ready",
        "requested_bounds": {
            "min_x": -10.0,
            "min_y": -20.0,
            "max_x": 30.0,
            "max_y": 40.0,
        },
        "nodes": [{"id": 11, "scope": "inner", "x": 1.5, "y": 2.5}],
        "edges": [],
    }


@pytest.mark.anyio
async def test_card_scope_details_route_returns_ordered_detail_records(
    async_client: AsyncClient,
) -> None:
    response = await async_client.post(
        "/api/v1/taxonomy/view/card-scopes/details",
        json={"route_path": "science/mathematics", "node_ids": [11, 77]},
    )

    assert response.status_code == 200
    assert [node["id"] for node in response.json()["nodes"]] == [11, 77]


@pytest.mark.anyio
async def test_card_scope_titles_route_returns_ordered_title_records(
    async_client: AsyncClient,
) -> None:
    response = await async_client.post(
        "/api/v1/taxonomy/view/card-scopes/titles",
        json={"route_path": "science/mathematics", "node_ids": [11, 77]},
    )

    assert response.status_code == 200
    assert response.json()["nodes"] == [
        {"id": 11, "title": "Inner 11"},
        {"id": 77, "title": "Outer 77"},
    ]


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("payload", "expected_message"),
    [
        ({"route_path": "science/mathematics", "node_ids": []}, "at least one node id"),
        ({"route_path": "science/mathematics", "node_ids": [11, 11]}, "duplicate node ids"),
        ({"route_path": "science/missing", "node_ids": [11]}, "outside the active graph"),
    ],
)
async def test_card_scope_detail_routes_return_400_for_invalid_requests(
    async_client: AsyncClient,
    app: FastAPI,
    payload: dict[str, object],
    expected_message: str,
) -> None:
    app.dependency_overrides[api_providers.get_taxonomy_service] = lambda: (
        _FakeTaxonomyInvalidDetailsService()
    )

    response = await async_client.post(
        "/api/v1/taxonomy/view/card-scopes/details",
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


@pytest.mark.anyio
async def test_card_scope_layout_routes_return_503_when_layout_is_not_ready(
    async_client: AsyncClient,
    app: FastAPI,
) -> None:
    app.dependency_overrides[api_providers.get_taxonomy_service] = lambda: (
        _FakeTaxonomyLayoutNotReadyService()
    )

    node_response = await async_client.get("/api/v1/taxonomy/view/nodes/2")
    path_response = await async_client.get("/api/v1/taxonomy/view/path/science/mathematics")
    layout_response = await async_client.get(
        "/api/v1/taxonomy/view/card-scopes/layout",
        params={
            "route_path": "science/mathematics",
            "min_x": -10.0,
            "min_y": -20.0,
            "max_x": 30.0,
            "max_y": 40.0,
        },
    )

    for response in (node_response, path_response, layout_response):
        assert response.status_code == 503
        assert response.headers["Retry-After"] == "10"
        error = response.json()["error"]
        assert error["code"] == "layout_not_ready"
        assert error["details"] == {
            "scope_kind": TAXONOMY_NODE_SCOPE_KIND,
            "taxonomy_node_id": 2,
        }


def _invalid_detail_error(*, node_ids: list[int], route_path: str) -> ApplicationError:
    message = "Card-scope detail request is invalid."
    if not node_ids:
        message = "Card-scope detail request requires at least one node id."
    elif len(node_ids) != len(set(node_ids)):
        message = "Card-scope detail request contains duplicate node ids."
    elif route_path == "science/missing":
        message = "Card-scope detail request references nodes outside the active graph."
    raise ApplicationError(
        code=ErrorCode.APPLICATION_TAXONOMY_INPUT_INVALID,
        message=message,
        hint="Send only unique node ids from the active card-scope graph and retry.",
    )


def _layout_not_ready_error() -> ApplicationError:
    return ApplicationError(
        code=ErrorCode.APPLICATION_TAXONOMY_LAYOUT_NOT_READY,
        message="Taxonomy card-scope layout is being prepared.",
        hint="Retry this request shortly.",
        safe_details={
            "scope_kind": TAXONOMY_NODE_SCOPE_KIND,
            "taxonomy_node_id": 2,
        },
    )
