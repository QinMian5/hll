"""
Abstract: HTTP embedding client used by search and ingestion worker flows.
Out of scope: Knowledge persistence orchestration and queue dispatch behavior.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx


def _extract_embedding_vector(payload: dict[str, Any]) -> list[float]:
    direct_embedding = payload.get("embedding")
    if isinstance(direct_embedding, list):
        return [float(value) for value in direct_embedding]

    data = payload.get("data")
    if isinstance(data, list) and data:
        first_item = data[0]
        if isinstance(first_item, dict) and isinstance(
            first_item.get("embedding"),
            list,
        ):
            return [float(value) for value in first_item["embedding"]]

    raise RuntimeError("Embedding response did not contain a usable embedding vector.")


@dataclass(slots=True, kw_only=True)
class EmbeddingClient:
    api_url: str
    model: str
    timeout_seconds: float
    api_key: str | None = None

    async def embed_text(self, text: str) -> list[float]:
        headers: dict[str, str] = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.post(
                self.api_url,
                json={
                    "model": self.model,
                    "input": text,
                },
                headers=headers,
            )
            response.raise_for_status()

        return _extract_embedding_vector(response.json())


def build_embedding_client(
    *,
    api_url: str,
    model: str,
    api_key: str,
    timeout_seconds: float,
) -> EmbeddingClient:
    return EmbeddingClient(
        api_url=api_url,
        model=model,
        api_key=api_key,
        timeout_seconds=timeout_seconds,
    )
