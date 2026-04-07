"""
Abstract: Unit tests for taxonomy view HTTP route contracts and payload shapes.
Out of scope: Taxonomy repository SQL behavior and classification orchestration.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import pytest
from fastapi import FastAPI
from httpx import AsyncClient

from core.errors import DomainError, ErrorCode
from entrypoints.api import providers as api_providers
from modules.taxonomy.schema import (
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
                    depth=0,
                    is_leaf=False,
                ),
                breadcrumb=[
                    TaxonomyViewNodeResponse(
                        id=1,
                        parent_id=None,
                        name="Science",
                        depth=0,
                        is_leaf=False,
                    )
                ],
                children=[
                    TaxonomyViewChildResponse(
                        id=2,
                        parent_id=1,
                        name="Mathematics",
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
                depth=1,
                is_leaf=True,
            ),
            breadcrumb=[
                TaxonomyViewNodeResponse(
                    id=1,
                    parent_id=None,
                    name="Science",
                    depth=0,
                    is_leaf=False,
                ),
                TaxonomyViewNodeResponse(
                    id=node_id,
                    parent_id=1,
                    name="Mathematics",
                    depth=1,
                    is_leaf=True,
                ),
            ],
            nodes=[],
            edges=[],
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


@pytest.fixture
def dependency_overrides() -> DependencyOverrides:
    return {
        api_providers.get_taxonomy_service: lambda: _FakeTaxonomyService(),
    }


@pytest.mark.anyio
async def test_root_view_route_returns_top_level_children(
    async_client: AsyncClient,
) -> None:
    response = await async_client.get("/taxonomy/view/root")

    assert response.status_code == 200
    payload = response.json()
    assert payload["breadcrumb"] == []
    assert payload["children"] == [
        {
            "id": 1,
            "parent_id": None,
            "name": "Science",
            "depth": 0,
            "is_leaf": False,
            "descendant_card_count": 12,
        }
    ]


@pytest.mark.anyio
async def test_node_view_route_returns_branch_payload_for_non_leaf(
    async_client: AsyncClient,
) -> None:
    response = await async_client.get("/taxonomy/view/nodes/1")

    assert response.status_code == 200
    payload = response.json()
    assert payload["node_kind"] == "branch"
    assert payload["current_node"]["id"] == 1
    assert payload["children"][0]["id"] == 2


@pytest.mark.anyio
async def test_node_view_route_returns_leaf_payload_for_leaf(
    async_client: AsyncClient,
) -> None:
    response = await async_client.get("/taxonomy/view/nodes/2")

    assert response.status_code == 200
    payload = response.json()
    assert payload["node_kind"] == "leaf"
    assert payload["current_node"]["id"] == 2
    assert payload["nodes"] == []
    assert payload["edges"] == []


@pytest.mark.anyio
async def test_taxonomy_view_routes_return_404_when_taxonomy_unavailable(
    async_client: AsyncClient,
    app: FastAPI,
) -> None:
    app.dependency_overrides[api_providers.get_taxonomy_service] = lambda: (
        _FakeTaxonomyNotFoundService()
    )

    root_response = await async_client.get("/taxonomy/view/root")
    node_response = await async_client.get("/taxonomy/view/nodes/123")

    assert root_response.status_code == 404
    assert node_response.status_code == 404
    assert root_response.json()["error"]["code"] == "DOMAIN_TAXONOMY_RESOURCE_NOT_FOUND"
    assert node_response.json()["error"]["code"] == "DOMAIN_TAXONOMY_RESOURCE_NOT_FOUND"
