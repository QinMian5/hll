"""
Abstract: HTTP handoff client for accepted cards entering knowledge ingestion.
Out of scope: Knowledge graph persistence and source-pipeline state transitions.
"""

from __future__ import annotations

import httpx

from source_pipeline.page_to_card.contracts import CardDraft


class KnowledgeIngestionHandoff:
    def __init__(
        self,
        *,
        base_url: str,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._client = httpx.AsyncClient(
            base_url=base_url,
            transport=transport,
            timeout=10.0,
        )

    async def handoff(
        self,
        *,
        candidate_id: int,
        card: CardDraft,
    ) -> None:
        response = await self._client.post(
            "/api/v1/cards",
            headers={"Idempotency-Key": _idempotency_key(candidate_id)},
            json=card.model_dump(mode="json"),
        )
        if response.status_code == 202:
            return

        response.raise_for_status()
        raise RuntimeError(
            f"Knowledge ingestion handoff expected 202 Accepted, received {response.status_code}."
        )

    async def aclose(self) -> None:
        await self._client.aclose()


def _idempotency_key(candidate_id: int) -> str:
    return f"source-pipeline:card-candidate:{candidate_id}"
