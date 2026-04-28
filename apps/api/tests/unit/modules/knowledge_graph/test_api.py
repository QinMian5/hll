"""
Abstract: Unit tests for private knowledge-graph card suggestion HTTP routes.
Out of scope: Browser session handling and repository persistence.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import pytest
from fastapi import FastAPI
from httpx import AsyncClient

from entrypoints.api import providers as api_providers
from modules.knowledge_graph.dto import CardSuggestedEditRecord
from modules.knowledge_graph.service import (
    CardSuggestedEditNoChangeError,
    CardVersionNotFoundError,
)

DependencyOverrides = dict[Callable[..., Any], Callable[..., Any]]


@dataclass(slots=True)
class _FakeKnowledgeGraphService:
    seen_payload: tuple[int, int, str, str, str] | None = None
    raise_not_found: bool = False
    raise_no_change: bool = False

    async def submit_card_suggested_edit(
        self,
        *,
        node_id: int,
        base_version: int,
        suggested_title: str,
        suggested_content: str,
        suggested_by_user_id: str,
    ) -> CardSuggestedEditRecord:
        if self.raise_not_found:
            raise CardVersionNotFoundError("missing")
        if self.raise_no_change:
            raise CardSuggestedEditNoChangeError("no change")
        self.seen_payload = (
            node_id,
            base_version,
            suggested_title,
            suggested_content,
            suggested_by_user_id,
        )
        return CardSuggestedEditRecord(
            id=99,
            node_id=node_id,
            base_version=base_version,
            suggested_title=suggested_title,
            suggested_content=suggested_content,
            suggested_by_user_id=suggested_by_user_id,
            status="pending",
            created_at=datetime(2026, 4, 28, 18, 0, tzinfo=UTC),
        )


@pytest.fixture
def dependency_overrides() -> DependencyOverrides:
    fake_service = _FakeKnowledgeGraphService()
    return {
        api_providers.get_knowledge_graph_service: lambda: fake_service,
    }


@pytest.mark.anyio
async def test_create_suggested_edit_returns_pending_response(
    async_client: AsyncClient,
    dependency_overrides: DependencyOverrides,
) -> None:
    response = await async_client.post(
        "/api/v1/cards/1/suggested-edits",
        json={
            "base_version": 2,
            "suggested_title": "Better title",
            "suggested_content": "Better content",
        },
        headers={"X-Knowledge-Suggested-By-User-Id": "logto-user-123"},
    )

    fake_service = dependency_overrides[api_providers.get_knowledge_graph_service]()
    assert response.status_code == 201
    assert response.json() == {
        "id": 99,
        "node_id": 1,
        "base_version": 2,
        "status": "pending",
        "created_at": "2026-04-28T18:00:00Z",
    }
    assert fake_service.seen_payload == (
        1,
        2,
        "Better title",
        "Better content",
        "logto-user-123",
    )


@pytest.mark.anyio
async def test_create_suggested_edit_rejects_missing_server_user_identity(
    async_client: AsyncClient,
    dependency_overrides: DependencyOverrides,
) -> None:
    response = await async_client.post(
        "/api/v1/cards/1/suggested-edits",
        json={
            "base_version": 2,
            "suggested_title": "Better title",
            "suggested_content": "Better content",
        },
    )

    fake_service = dependency_overrides[api_providers.get_knowledge_graph_service]()
    assert response.status_code == 422
    assert fake_service.seen_payload is None


@pytest.mark.anyio
async def test_create_suggested_edit_returns_404_for_unknown_base_version(
    async_client: AsyncClient,
    app: FastAPI,
) -> None:
    app.dependency_overrides[api_providers.get_knowledge_graph_service] = lambda: (
        _FakeKnowledgeGraphService(raise_not_found=True)
    )

    response = await async_client.post(
        "/api/v1/cards/1/suggested-edits",
        json={
            "base_version": 9,
            "suggested_title": "Better title",
            "suggested_content": "Better content",
        },
        headers={"X-Knowledge-Suggested-By-User-Id": "logto-user-123"},
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "DOMAIN_KNOWLEDGE_RESOURCE_NOT_FOUND"


@pytest.mark.anyio
async def test_create_suggested_edit_returns_422_for_noop_suggestion(
    async_client: AsyncClient,
    app: FastAPI,
) -> None:
    app.dependency_overrides[api_providers.get_knowledge_graph_service] = lambda: (
        _FakeKnowledgeGraphService(raise_no_change=True)
    )

    response = await async_client.post(
        "/api/v1/cards/1/suggested-edits",
        json={
            "base_version": 1,
            "suggested_title": "Same title",
            "suggested_content": "Same content",
        },
        headers={"X-Knowledge-Suggested-By-User-Id": "logto-user-123"},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "DOMAIN_KNOWLEDGE_RULE_VIOLATION"
