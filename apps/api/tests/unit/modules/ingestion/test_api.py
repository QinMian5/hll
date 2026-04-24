"""
Abstract: Unit tests for the ingestion HTTP acceptance contract.
Out of scope: Queue broker reliability and worker-side persistence logic.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import pytest
from fastapi import FastAPI
from httpx import AsyncClient

from entrypoints.api import providers as api_providers
from modules.ingestion.schema import IngestionAcceptedResponse, IngestionCreateRequest
from modules.ingestion.service import IngestionIdempotencyConflictError

DependencyOverrides = dict[Callable[..., Any], Callable[..., Any]]


@dataclass(slots=True)
class _FakeIngestionService:
    seen_idempotency_key: str | None = None

    async def accept(
        self,
        *,
        payload: IngestionCreateRequest,
        request_id: str,
        idempotency_key: str | None = None,
    ) -> IngestionAcceptedResponse:
        assert payload.title == "Title"
        assert payload.content == "Content"
        assert request_id
        self.seen_idempotency_key = idempotency_key
        return IngestionAcceptedResponse(
            accepted=True,
            ingestion_id="ing_1234567890abcdef1234567890abcdef",
        )


@pytest.fixture
def dependency_overrides() -> DependencyOverrides:
    fake_service = _FakeIngestionService()
    return {
        api_providers.get_ingestion_service: lambda: fake_service,
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
async def test_ingestion_passes_idempotency_key_header_to_service(
    async_client: AsyncClient,
    dependency_overrides: DependencyOverrides,
) -> None:
    response = await async_client.post(
        "/api/v1/cards",
        json={"title": "Title", "content": "Content"},
        headers={"Idempotency-Key": "source-candidate-1"},
    )

    assert response.status_code == 202
    fake_service = dependency_overrides[api_providers.get_ingestion_service]()
    assert fake_service.seen_idempotency_key == "source-candidate-1"


@pytest.mark.anyio
async def test_ingestion_passes_none_when_idempotency_key_header_is_missing(
    async_client: AsyncClient,
    dependency_overrides: DependencyOverrides,
) -> None:
    response = await async_client.post(
        "/api/v1/cards",
        json={"title": "Title", "content": "Content"},
    )

    assert response.status_code == 202
    fake_service = dependency_overrides[api_providers.get_ingestion_service]()
    assert fake_service.seen_idempotency_key is None


@pytest.mark.anyio
async def test_ingestion_idempotency_conflict_returns_409_error_envelope(
    app: FastAPI,
    async_client: AsyncClient,
) -> None:
    class _ConflictingIngestionService(_FakeIngestionService):
        async def accept(
            self,
            *,
            payload: IngestionCreateRequest,
            request_id: str,
            idempotency_key: str | None = None,
        ) -> IngestionAcceptedResponse:
            raise IngestionIdempotencyConflictError(
                idempotency_key=idempotency_key or "missing",
            )

    app.dependency_overrides[api_providers.get_ingestion_service] = lambda: (
        _ConflictingIngestionService()
    )

    response = await async_client.post(
        "/api/v1/cards",
        json={"title": "Title", "content": "Content"},
        headers={"Idempotency-Key": "source-candidate-1"},
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "APPLICATION_INGESTION_STATE_CONFLICT"


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
