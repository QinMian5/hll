"""
Abstract: Unit tests for ingestion worker task orchestration.
Out of scope: Dramatiq runtime process management and broker transport behavior.
"""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from modules.ingestion.workers import process_ingestion_job


@dataclass(slots=True)
class _FakeEmbeddingClient:
    async def embed_text(self, text: str) -> list[float]:
        assert text == "Content"
        return [0.7, 0.8]


@dataclass(slots=True)
class _FakeKnowledgeService:
    seen: list[tuple[str, str, list[float]]]

    async def materialize_card_from_ingestion(
        self,
        *,
        title: str,
        content: str,
        embedding: list[float],
    ) -> int:
        self.seen.append((title, content, embedding))
        return 101


@pytest.mark.anyio
async def test_process_ingestion_job_embeds_and_materializes() -> None:
    knowledge = _FakeKnowledgeService(seen=[])
    node_id = await process_ingestion_job(
        title="Title",
        content="Content",
        embedding_client=_FakeEmbeddingClient(),
        knowledge_graph_write_port=knowledge,
    )

    assert node_id == 101
    assert knowledge.seen == [("Title", "Content", [0.7, 0.8])]
