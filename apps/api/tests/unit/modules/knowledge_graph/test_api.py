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
from modules.knowledge_graph.dto import (
    CardProposalRecord,
    CardProposalType,
    CardSuggestedEditRecord,
)
from modules.knowledge_graph.service import (
    CardProposalPermissionError,
    CardSuggestedEditNoChangeError,
    CardVersionNotFoundError,
)

DependencyOverrides = dict[Callable[..., Any], Callable[..., Any]]


@dataclass(slots=True)
class _FakeKnowledgeGraphService:
    seen_payload: tuple[int, int, str, str, str, str] | None = None
    seen_proposal_payload: dict[str, object | None] | None = None
    seen_accept_payload: tuple[int, str, str | None] | None = None
    raise_not_found: bool = False
    raise_no_change: bool = False
    raise_permission: bool = False

    async def submit_card_suggested_edit(
        self,
        *,
        node_id: int,
        base_version: int,
        suggested_title: str,
        suggested_content: str,
        suggested_by_user_id: str,
        reason: str,
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
            reason,
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

    async def submit_card_proposal(
        self,
        *,
        proposal_type: CardProposalType,
        submitted_by_user_id: str,
        proposed_title: str | None,
        proposed_content: str | None,
        target_node_id: int | None,
        base_version: int | None,
        suggested_title: str | None,
        suggested_content: str | None,
        reason: str,
    ) -> CardProposalRecord:
        if self.raise_not_found:
            raise CardVersionNotFoundError("missing")
        if self.raise_no_change:
            raise CardSuggestedEditNoChangeError("no change")
        self.seen_proposal_payload = {
            "proposal_type": proposal_type,
            "submitted_by_user_id": submitted_by_user_id,
            "proposed_title": proposed_title,
            "proposed_content": proposed_content,
            "target_node_id": target_node_id,
            "base_version": base_version,
            "suggested_title": suggested_title,
            "suggested_content": suggested_content,
            "reason": reason,
        }
        response_payload = {
            key: value
            for key, value in self.seen_proposal_payload.items()
            if key not in {"proposal_type", "submitted_by_user_id", "reason"} and value is not None
        }
        return CardProposalRecord(
            id=199,
            proposal_type=proposal_type,
            reason=reason,
            status="pending_review",
            submitted_by_user_id=submitted_by_user_id,
            reviewed_by_user_id=None,
            review_note=None,
            payload=response_payload,
            created_at=datetime(2026, 4, 28, 18, 0, tzinfo=UTC),
            updated_at=datetime(2026, 4, 28, 18, 0, tzinfo=UTC),
            reviewed_at=None,
        )

    async def accept_card_proposal(
        self,
        *,
        proposal_id: int,
        reviewer_user_id: str,
        review_note: str | None,
    ) -> CardProposalRecord:
        if self.raise_permission:
            raise CardProposalPermissionError("forbidden")
        self.seen_accept_payload = (proposal_id, reviewer_user_id, review_note)
        return CardProposalRecord(
            id=proposal_id,
            proposal_type="edit",
            reason="The current card needs clearer wording.",
            status="accepted_applied",
            submitted_by_user_id="contributor",
            reviewed_by_user_id=reviewer_user_id,
            review_note=review_note,
            payload={
                "target_node_id": 1,
                "base_version": 2,
                "suggested_title": "Better title",
                "suggested_content": "Better content",
            },
            created_at=datetime(2026, 4, 28, 18, 0, tzinfo=UTC),
            updated_at=datetime(2026, 4, 28, 18, 0, tzinfo=UTC),
            reviewed_at=datetime(2026, 4, 28, 19, 0, tzinfo=UTC),
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
            "reason": "The current card needs clearer wording.",
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
        "The current card needs clearer wording.",
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
            "reason": "The current card needs clearer wording.",
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
            "reason": "The current card needs clearer wording.",
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
            "reason": "The current card needs clearer wording.",
        },
        headers={"X-Knowledge-Suggested-By-User-Id": "logto-user-123"},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "DOMAIN_KNOWLEDGE_RULE_VIOLATION"


@pytest.mark.anyio
async def test_create_card_proposal_uses_actor_header_identity(
    async_client: AsyncClient,
    dependency_overrides: DependencyOverrides,
) -> None:
    response = await async_client.post(
        "/api/v1/card-proposals",
        json={
            "proposal_type": "edit",
            "target_node_id": 1,
            "base_version": 2,
            "suggested_title": "Better title",
            "suggested_content": "Better content",
            "reason": "The current card needs clearer wording.",
        },
        headers={"X-Knowledge-Actor-User-Id": "logto-user-123"},
    )

    fake_service = dependency_overrides[api_providers.get_knowledge_graph_service]()
    assert response.status_code == 201
    assert response.json() == {
        "id": 199,
        "proposal_type": "edit",
        "reason": "The current card needs clearer wording.",
        "status": "pending_review",
        "submitted_by_user_id": "logto-user-123",
        "reviewed_by_user_id": None,
        "review_note": None,
        "payload": {
            "target_node_id": 1,
            "base_version": 2,
            "suggested_title": "Better title",
            "suggested_content": "Better content",
        },
        "created_at": "2026-04-28T18:00:00Z",
        "updated_at": "2026-04-28T18:00:00Z",
        "reviewed_at": None,
    }
    assert fake_service.seen_proposal_payload == {
        "proposal_type": "edit",
        "submitted_by_user_id": "logto-user-123",
        "proposed_title": None,
        "proposed_content": None,
        "target_node_id": 1,
        "base_version": 2,
        "suggested_title": "Better title",
        "suggested_content": "Better content",
        "reason": "The current card needs clearer wording.",
    }


@pytest.mark.anyio
async def test_create_card_proposal_rejects_missing_common_reason(
    async_client: AsyncClient,
    dependency_overrides: DependencyOverrides,
) -> None:
    response = await async_client.post(
        "/api/v1/card-proposals",
        json={
            "proposal_type": "edit",
            "target_node_id": 1,
            "base_version": 2,
            "suggested_title": "Better title",
            "suggested_content": "Better content",
        },
        headers={"X-Knowledge-Actor-User-Id": "logto-user-123"},
    )

    fake_service = dependency_overrides[api_providers.get_knowledge_graph_service]()
    assert response.status_code == 422
    assert fake_service.seen_proposal_payload is None


@pytest.mark.anyio
async def test_accept_card_proposal_uses_actor_header_as_reviewer(
    async_client: AsyncClient,
    dependency_overrides: DependencyOverrides,
) -> None:
    response = await async_client.post(
        "/api/v1/card-proposals/199/accept",
        json={"review_note": "Looks good."},
        headers={"X-Knowledge-Actor-User-Id": "reviewer-user"},
    )

    fake_service = dependency_overrides[api_providers.get_knowledge_graph_service]()
    assert response.status_code == 200
    assert response.json()["status"] == "accepted_applied"
    assert response.json()["reviewed_by_user_id"] == "reviewer-user"
    assert fake_service.seen_accept_payload == (199, "reviewer-user", "Looks good.")


@pytest.mark.anyio
async def test_accept_card_proposal_returns_403_without_reviewer_role(
    async_client: AsyncClient,
    app: FastAPI,
) -> None:
    app.dependency_overrides[api_providers.get_knowledge_graph_service] = lambda: (
        _FakeKnowledgeGraphService(raise_permission=True)
    )

    response = await async_client.post(
        "/api/v1/card-proposals/199/accept",
        json={"review_note": "Looks good."},
        headers={"X-Knowledge-Actor-User-Id": "ordinary-user"},
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "DOMAIN_KNOWLEDGE_PERMISSION_DENIED"
