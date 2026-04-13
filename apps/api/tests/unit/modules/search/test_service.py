"""
Abstract: Unit tests for search-service orchestration and output-shape constraints.
Out of scope: FastAPI transport validation and repository SQL behavior.
"""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from modules.search.service import SearchService

TEST_MAX_MATCHED = 3
TEST_MAX_CONNECTED = 7


@dataclass(slots=True)
class _KnowledgeCardMatch:
    title: str
    content: str
    node_id: int | None = None


@dataclass(slots=True)
class _FakeEmbeddingClient:
    last_text: str | None = None

    async def embed_text(self, text: str) -> list[float]:
        self.last_text = text
        return [0.1, 0.2, 0.3]


@dataclass(slots=True)
class _FakeKnowledgeService:
    matched_limit_seen: int | None = None
    connected_limit_seen: int | None = None

    async def search_searchable_cards(
        self,
        *,
        query_embedding: list[float],
        limit: int,
    ) -> list[_KnowledgeCardMatch]:
        assert query_embedding == [0.1, 0.2, 0.3]
        self.matched_limit_seen = limit
        return [
            _KnowledgeCardMatch(node_id=11, title="A", content="alpha"),
            _KnowledgeCardMatch(node_id=12, title="B", content="beta"),
        ]

    async def get_connected_titles(
        self,
        *,
        matched_node_ids: list[int],
        excluded_titles: set[str],
        limit: int,
    ) -> list[str]:
        assert matched_node_ids == [11, 12]
        assert excluded_titles == {"A", "B"}
        self.connected_limit_seen = limit
        return ["C", "D"]


@pytest.mark.anyio
async def test_search_returns_matched_cards_with_only_title_and_content() -> None:
    embedding_client = _FakeEmbeddingClient()
    knowledge_service = _FakeKnowledgeService()
    service = SearchService(
        knowledge_graph_read_port=knowledge_service,
        embedding_client=embedding_client,
        max_matched=TEST_MAX_MATCHED,
        max_connected=TEST_MAX_CONNECTED,
    )

    response = await service.search("what is card b")

    assert embedding_client.last_text == "what is card b"
    assert [item.model_dump() for item in response.matched_cards] == [
        {"title": "A", "content": "alpha"},
        {"title": "B", "content": "beta"},
    ]
    assert response.connected_titles == ["C", "D"]


@pytest.mark.anyio
async def test_search_uses_constructor_supplied_limits() -> None:
    knowledge_service = _FakeKnowledgeService()
    service = SearchService(
        knowledge_graph_read_port=knowledge_service,
        embedding_client=_FakeEmbeddingClient(),
        max_matched=TEST_MAX_MATCHED,
        max_connected=TEST_MAX_CONNECTED,
    )

    await service.search("q")

    assert knowledge_service.matched_limit_seen == TEST_MAX_MATCHED
    assert knowledge_service.connected_limit_seen == TEST_MAX_CONNECTED
