"""
Abstract: Unit tests for the ingestion HTTP acceptance contract.
Out of scope: Queue broker reliability and worker-side persistence logic.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import pytest
from httpx import AsyncClient

from entrypoints.api import providers as api_providers
from modules.ingestion.schema import IngestionAcceptedResponse, IngestionCreateRequest

DependencyOverrides = dict[Callable[..., Any], Callable[..., Any]]


@dataclass(slots=True)
class _FakeIngestionService:
    async def accept(
        self,
        *,
        payload: IngestionCreateRequest,
        request_id: str,
    ) -> IngestionAcceptedResponse:
        assert payload.title == "Title"
        assert payload.content == "Content"
        assert request_id
        return IngestionAcceptedResponse(
            accepted=True,
            ingestion_id="ing_1234567890abcdef1234567890abcdef",
        )


@pytest.fixture
def dependency_overrides() -> DependencyOverrides:
    return {
        api_providers.get_ingestion_service: lambda: _FakeIngestionService(),
    }


@pytest.mark.anyio
async def test_ingestion_valid_payload_returns_202(async_client: AsyncClient) -> None:
    response = await async_client.post(
        "/api/v1/cards",
        json={"title": "Title", "content": "Content"},
    )

    assert response.status_code == 202
    assert response.json() == {
        "accepted": True,
        "ingestion_id": "ing_1234567890abcdef1234567890abcdef",
    }


@pytest.mark.anyio
async def test_ingestion_invalid_payload_returns_422_error_envelope(
    async_client: AsyncClient,
) -> None:
    response = await async_client.post(
        "/api/v1/cards",
        json={"title": "", "content": "Content"},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "APPLICATION_API_INPUT_INVALID"
