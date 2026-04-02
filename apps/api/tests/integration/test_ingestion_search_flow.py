"""
Abstract: Integration-style orchestration test across ingestion worker processing and
searchable knowledge state.
Out of scope: Real PostgreSQL/Redis networking and process-level worker runtime.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from modules.ingestion.workers import process_ingestion_job


@dataclass(slots=True)
class _StoredCard:
    node_id: int
    title: str
    content: str
    embedding: list[float]


@dataclass(slots=True)
class _InMemoryKnowledgeService:
    cards: list[_StoredCard] = field(default_factory=list)

    async def materialize_card_from_ingestion(
        self,
        *,
        title: str,
        content: str,
        embedding: list[float],
    ) -> int:
        node_id = len(self.cards) + 1
        self.cards.append(
            _StoredCard(
                node_id=node_id,
                title=title,
                content=content,
                embedding=embedding,
            )
        )
        return node_id

    async def search_searchable_cards(self) -> list[dict[str, str]]:
        return [{"title": card.title, "content": card.content} for card in self.cards]


@dataclass(slots=True)
class _StaticEmbeddingClient:
    async def embed_text(self, text: str) -> list[float]:
        assert text == "Alpha"
        return [0.2, 0.4, 0.6]


@pytest.mark.integration
@pytest.mark.anyio
async def test_ingestion_worker_materializes_card_that_is_searchable() -> None:
    knowledge_service = _InMemoryKnowledgeService()

    node_id = await process_ingestion_job(
        title="Card A",
        content="Alpha",
        embedding_client=_StaticEmbeddingClient(),
        knowledge_graph_write_port=knowledge_service,
    )
    searchable_cards = await knowledge_service.search_searchable_cards()

    assert node_id == 1
    assert searchable_cards == [{"title": "Card A", "content": "Alpha"}]
