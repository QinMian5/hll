"""
Abstract: Integration tests for accepted-card handoff into knowledge ingestion.
Out of scope: Knowledge API persistence behavior and source-pipeline polling.
"""

from __future__ import annotations

import httpx
import pytest

from source_pipeline.page_to_card.contracts import CardDraft
from source_pipeline.pipeline_handoff.knowledge_ingestion import KnowledgeIngestionHandoff

pytestmark = [pytest.mark.integration, pytest.mark.anyio]


async def test_handoff_posts_card_to_knowledge_ingestion_with_stable_idempotency_key() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        assert request.method == "POST"
        assert str(request.url) == "http://knowledge-api/api/v1/cards"
        assert request.headers["Idempotency-Key"] == "source-pipeline:card-candidate:42"
        assert request.read() == b'{"title":"Quantum State","content":"A state description."}'
        return httpx.Response(
            202,
            json={
                "accepted": True,
                "ingestion_id": "ing_0123456789abcdef0123456789abcdef",
            },
        )

    handoff = KnowledgeIngestionHandoff(
        base_url="http://knowledge-api",
        transport=httpx.MockTransport(handler),
    )

    await handoff.handoff(
        candidate_id=42,
        card=CardDraft(title="Quantum State", content="A state description."),
    )
    await handoff.handoff(
        candidate_id=42,
        card=CardDraft(title="Quantum State", content="A state description."),
    )

    assert len(requests) == 2


async def test_handoff_raises_for_non_accepted_response() -> None:
    handoff = KnowledgeIngestionHandoff(
        base_url="http://knowledge-api",
        transport=httpx.MockTransport(lambda request: httpx.Response(500)),
    )

    with pytest.raises(httpx.HTTPStatusError):
        await handoff.handoff(
            candidate_id=42,
            card=CardDraft(title="Quantum State", content="A state description."),
        )


async def test_handoff_does_not_swallow_transport_errors() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection failed", request=request)

    handoff = KnowledgeIngestionHandoff(
        base_url="http://knowledge-api",
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(httpx.ConnectError):
        await handoff.handoff(
            candidate_id=42,
            card=CardDraft(title="Quantum State", content="A state description."),
        )
