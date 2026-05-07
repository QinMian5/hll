"""
Abstract: Unit tests for search-service orchestration and output-shape constraints.
Out of scope: FastAPI transport validation and repository SQL behavior.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from logging import LogRecord
from typing import Literal

import pytest

from core.errors import ErrorCode, InfrastructureError
from modules.knowledge_graph.dto import KnowledgeCardMatch, SearchableCardResult
from modules.search.schema import MatchedCardResponse, SearchResponse
from modules.search.service import SearchService
from shared.integrations.embedding_client import EmbeddingServiceUnavailableError

TEST_MAX_MATCHED = 3
TEST_MAX_CONNECTED = 7
TEST_VECTOR_CANDIDATE_POOL_SIZE = 64


@dataclass(slots=True)
class _FakeEmbeddingClient:
    last_text: str | None = None
    calls: int = 0

    async def embed_text(self, text: str) -> list[float]:
        self.calls += 1
        self.last_text = text
        return [0.1, 0.2, 0.3]


class _UnavailableEmbeddingClient:
    async def embed_text(self, _text: str) -> list[float]:
        raise EmbeddingServiceUnavailableError("embedding request failed")


@dataclass(slots=True)
class _FakeKnowledgeService:
    query_text_seen: str | None = None
    matched_limit_seen: int | None = None
    vector_candidate_limit_seen: int | None = None
    connected_limit_seen: int | None = None
    expected_query_embedding: list[float] = field(default_factory=lambda: [0.1, 0.2, 0.3])
    vector_candidate_count: int = 8
    search_calls: int = 0
    connected_title_calls: int = 0

    async def search_searchable_cards(
        self,
        *,
        query_text: str,
        query_embedding: list[float],
        limit: int,
        vector_candidate_limit: int,
    ) -> SearchableCardResult:
        self.search_calls += 1
        self.query_text_seen = query_text
        assert query_embedding == self.expected_query_embedding
        self.matched_limit_seen = limit
        self.vector_candidate_limit_seen = vector_candidate_limit
        return SearchableCardResult(
            matches=[
                KnowledgeCardMatch(
                    node_id=11,
                    current_version=1,
                    title="A",
                    content="alpha",
                ),
                KnowledgeCardMatch(
                    node_id=12,
                    current_version=4,
                    title="B",
                    content="beta",
                ),
            ],
            vector_candidate_count=self.vector_candidate_count,
        )

    async def get_connected_titles(
        self,
        *,
        matched_node_ids: list[int],
        excluded_titles: set[str],
        limit: int,
    ) -> list[str]:
        self.connected_title_calls += 1
        assert matched_node_ids == [11, 12]
        assert excluded_titles == {"A", "B"}
        self.connected_limit_seen = limit
        return ["C", "D"]


@dataclass(slots=True)
class _FakeResponseCache:
    cached_response: SearchResponse | None = None
    fail_get: bool = False
    fail_set: bool = False
    get_calls: list[tuple[str, str, int, int, int]] = field(default_factory=list)
    set_calls: list[tuple[str, str, int, int, int, SearchResponse]] = field(default_factory=list)

    async def get(
        self,
        *,
        query: str,
        embedding_model: str,
        max_matched: int,
        max_connected: int,
        vector_candidate_pool_size: int,
    ) -> SearchResponse | None:
        self.get_calls.append(
            (
                query,
                embedding_model,
                max_matched,
                max_connected,
                vector_candidate_pool_size,
            )
        )
        if self.fail_get:
            raise RuntimeError("response cache unavailable")
        return self.cached_response

    async def set(
        self,
        *,
        query: str,
        embedding_model: str,
        max_matched: int,
        max_connected: int,
        vector_candidate_pool_size: int,
        response: SearchResponse,
    ) -> None:
        self.set_calls.append(
            (
                query,
                embedding_model,
                max_matched,
                max_connected,
                vector_candidate_pool_size,
                response,
            )
        )
        if self.fail_set:
            raise RuntimeError("response cache write failed")


@dataclass(slots=True)
class _FakeEmbeddingCache:
    cached_embedding: list[float] | None = None
    fail_get: bool = False
    fail_set: bool = False
    get_calls: list[tuple[str, str]] = field(default_factory=list)
    set_calls: list[tuple[str, str, list[float]]] = field(default_factory=list)

    async def get(self, *, query: str, embedding_model: str) -> list[float] | None:
        self.get_calls.append((query, embedding_model))
        if self.fail_get:
            raise RuntimeError("embedding cache unavailable")
        return self.cached_embedding

    async def set(self, *, query: str, embedding_model: str, embedding: list[float]) -> None:
        self.set_calls.append((query, embedding_model, list(embedding)))
        if self.fail_set:
            raise RuntimeError("embedding cache write failed")


def _cached_response() -> SearchResponse:
    return SearchResponse(
        matched_cards=[
            MatchedCardResponse(
                node_id=99,
                current_version=3,
                title="Cached",
                content="cached content",
            )
        ],
        connected_titles=["Cached neighbor"],
    )


def _search_timing_record(caplog: pytest.LogCaptureFixture) -> LogRecord:
    records = [record for record in caplog.records if record.message == "search.timing"]
    assert len(records) == 1
    return records[0]


@pytest.mark.anyio
async def test_search_returns_matched_cards_with_version_identity() -> None:
    embedding_client = _FakeEmbeddingClient()
    knowledge_service = _FakeKnowledgeService()
    service = SearchService(
        knowledge_graph_read_port=knowledge_service,
        embedding_client=embedding_client,
        max_matched=TEST_MAX_MATCHED,
        max_connected=TEST_MAX_CONNECTED,
        vector_candidate_pool_size=TEST_VECTOR_CANDIDATE_POOL_SIZE,
    )

    response = await service.search("what is card b")

    assert embedding_client.last_text == "what is card b"
    assert knowledge_service.query_text_seen == "what is card b"
    assert [item.model_dump() for item in response.matched_cards] == [
        {"node_id": 11, "current_version": 1, "title": "A", "content": "alpha"},
        {"node_id": 12, "current_version": 4, "title": "B", "content": "beta"},
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
        vector_candidate_pool_size=TEST_VECTOR_CANDIDATE_POOL_SIZE,
    )

    await service.search("q")

    assert knowledge_service.matched_limit_seen == TEST_MAX_MATCHED
    assert knowledge_service.vector_candidate_limit_seen == TEST_VECTOR_CANDIDATE_POOL_SIZE
    assert knowledge_service.connected_limit_seen == TEST_MAX_CONNECTED


@pytest.mark.anyio
async def test_search_response_cache_hit_skips_embedding_and_knowledge_ports() -> None:
    embedding_client = _FakeEmbeddingClient()
    knowledge_service = _FakeKnowledgeService()
    response_cache = _FakeResponseCache(cached_response=_cached_response())
    service = SearchService(
        knowledge_graph_read_port=knowledge_service,
        embedding_client=embedding_client,
        max_matched=TEST_MAX_MATCHED,
        max_connected=TEST_MAX_CONNECTED,
        vector_candidate_pool_size=TEST_VECTOR_CANDIDATE_POOL_SIZE,
        response_cache=response_cache,
        embedding_model="text-embedding-3-small",
    )

    response = await service.search("cache me")

    assert response == _cached_response()
    assert response_cache.get_calls == [
        (
            "cache me",
            "text-embedding-3-small",
            TEST_MAX_MATCHED,
            TEST_MAX_CONNECTED,
            TEST_VECTOR_CANDIDATE_POOL_SIZE,
        )
    ]
    assert embedding_client.calls == 0
    assert knowledge_service.search_calls == 0
    assert knowledge_service.connected_title_calls == 0


@pytest.mark.anyio
async def test_search_response_cache_miss_writes_successful_response() -> None:
    response_cache = _FakeResponseCache()
    service = SearchService(
        knowledge_graph_read_port=_FakeKnowledgeService(),
        embedding_client=_FakeEmbeddingClient(),
        max_matched=TEST_MAX_MATCHED,
        max_connected=TEST_MAX_CONNECTED,
        vector_candidate_pool_size=TEST_VECTOR_CANDIDATE_POOL_SIZE,
        response_cache=response_cache,
        embedding_model="text-embedding-3-small",
    )

    response = await service.search("cache miss")

    assert response_cache.set_calls == [
        (
            "cache miss",
            "text-embedding-3-small",
            TEST_MAX_MATCHED,
            TEST_MAX_CONNECTED,
            TEST_VECTOR_CANDIDATE_POOL_SIZE,
            response,
        )
    ]


@pytest.mark.anyio
async def test_search_embedding_cache_hit_skips_embedding_provider() -> None:
    embedding_client = _FakeEmbeddingClient()
    embedding_cache = _FakeEmbeddingCache(cached_embedding=[0.9, 0.8, 0.7])
    knowledge_service = _FakeKnowledgeService(expected_query_embedding=[0.9, 0.8, 0.7])
    service = SearchService(
        knowledge_graph_read_port=knowledge_service,
        embedding_client=embedding_client,
        max_matched=TEST_MAX_MATCHED,
        max_connected=TEST_MAX_CONNECTED,
        vector_candidate_pool_size=TEST_VECTOR_CANDIDATE_POOL_SIZE,
        embedding_cache=embedding_cache,
        embedding_model="text-embedding-3-small",
    )

    await service.search("cached embedding")

    assert embedding_cache.get_calls == [("cached embedding", "text-embedding-3-small")]
    assert embedding_client.calls == 0
    assert knowledge_service.search_calls == 1


@pytest.mark.anyio
async def test_search_embedding_cache_miss_writes_embedding_after_provider_call() -> None:
    embedding_cache = _FakeEmbeddingCache()
    service = SearchService(
        knowledge_graph_read_port=_FakeKnowledgeService(),
        embedding_client=_FakeEmbeddingClient(),
        max_matched=TEST_MAX_MATCHED,
        max_connected=TEST_MAX_CONNECTED,
        vector_candidate_pool_size=TEST_VECTOR_CANDIDATE_POOL_SIZE,
        embedding_cache=embedding_cache,
        embedding_model="text-embedding-3-small",
    )

    await service.search("new embedding")

    assert embedding_cache.set_calls == [
        ("new embedding", "text-embedding-3-small", [0.1, 0.2, 0.3])
    ]


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("cache_name", "operation"),
    [
        ("response", "read"),
        ("response", "write"),
        ("embedding", "read"),
        ("embedding", "write"),
    ],
)
async def test_search_cache_failures_are_logged_and_treated_as_misses(
    cache_name: Literal["response", "embedding"],
    operation: Literal["read", "write"],
    caplog: pytest.LogCaptureFixture,
) -> None:
    response_cache = _FakeResponseCache(
        fail_get=cache_name == "response" and operation == "read",
        fail_set=cache_name == "response" and operation == "write",
    )
    embedding_cache = _FakeEmbeddingCache(
        fail_get=cache_name == "embedding" and operation == "read",
        fail_set=cache_name == "embedding" and operation == "write",
    )
    service = SearchService(
        knowledge_graph_read_port=_FakeKnowledgeService(),
        embedding_client=_FakeEmbeddingClient(),
        max_matched=TEST_MAX_MATCHED,
        max_connected=TEST_MAX_CONNECTED,
        vector_candidate_pool_size=TEST_VECTOR_CANDIDATE_POOL_SIZE,
        response_cache=response_cache,
        embedding_cache=embedding_cache,
        embedding_model="text-embedding-3-small",
    )

    response = await service.search("cache failure")

    assert [item.title for item in response.matched_cards] == ["A", "B"]
    assert "Search cache failure" in caplog.text


@pytest.mark.anyio
async def test_search_maps_embedding_unavailability_to_infrastructure_error() -> None:
    service = SearchService(
        knowledge_graph_read_port=_FakeKnowledgeService(),
        embedding_client=_UnavailableEmbeddingClient(),
        max_matched=TEST_MAX_MATCHED,
        max_connected=TEST_MAX_CONNECTED,
        vector_candidate_pool_size=TEST_VECTOR_CANDIDATE_POOL_SIZE,
    )

    with pytest.raises(InfrastructureError) as exc_info:
        await service.search("q")

    assert exc_info.value.code is ErrorCode.INFRA_EMBEDDING_SERVICE_UNAVAILABLE


@pytest.mark.anyio
async def test_search_response_cache_hit_logs_timing_without_raw_query(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level("INFO")
    response_cache = _FakeResponseCache(cached_response=_cached_response())
    service = SearchService(
        knowledge_graph_read_port=_FakeKnowledgeService(),
        embedding_client=_FakeEmbeddingClient(),
        max_matched=TEST_MAX_MATCHED,
        max_connected=TEST_MAX_CONNECTED,
        vector_candidate_pool_size=TEST_VECTOR_CANDIDATE_POOL_SIZE,
        response_cache=response_cache,
        embedding_model="text-embedding-3-small",
    )

    await service.search("cache hit raw query")

    record = _search_timing_record(caplog)
    assert record.search_status == "cache_hit"
    assert record.search_cache_hit is True
    assert record.search_matched_count == 1
    assert record.search_connected_title_count == 1
    assert record.search_vector_candidate_pool_size == TEST_VECTOR_CANDIDATE_POOL_SIZE
    assert "cache hit raw query" not in caplog.text
    assert all(value != "cache hit raw query" for value in record.__dict__.values())


@pytest.mark.anyio
async def test_search_cache_miss_logs_stage_timings_and_counts(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level("INFO")
    service = SearchService(
        knowledge_graph_read_port=_FakeKnowledgeService(vector_candidate_count=13),
        embedding_client=_FakeEmbeddingClient(),
        max_matched=TEST_MAX_MATCHED,
        max_connected=TEST_MAX_CONNECTED,
        vector_candidate_pool_size=TEST_VECTOR_CANDIDATE_POOL_SIZE,
        response_cache=_FakeResponseCache(),
        embedding_cache=_FakeEmbeddingCache(),
        embedding_model="text-embedding-3-small",
    )

    await service.search("cache miss raw query")

    record = _search_timing_record(caplog)
    assert record.search_status == "ok"
    assert record.search_cache_hit is False
    assert record.search_embedding_cache_hit is False
    assert record.search_max_matched == TEST_MAX_MATCHED
    assert record.search_max_connected == TEST_MAX_CONNECTED
    assert record.search_vector_candidate_pool_size == TEST_VECTOR_CANDIDATE_POOL_SIZE
    assert record.search_vector_candidate_count == 13
    assert record.search_matched_count == 2
    assert record.search_connected_title_count == 2
    for field_name in (
        "search_timing_cache_get_ms",
        "search_timing_embedding_cache_get_ms",
        "search_timing_embedding_ms",
        "search_timing_retrieval_ms",
        "search_timing_connected_titles_ms",
        "search_timing_cache_set_ms",
        "search_timing_total_ms",
    ):
        assert getattr(record, field_name) >= 0.0
    assert "cache miss raw query" not in caplog.text
    assert all(value != "cache miss raw query" for value in record.__dict__.values())


@pytest.mark.anyio
async def test_search_embedding_failure_logs_timing_status_without_raw_query(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level("INFO")
    service = SearchService(
        knowledge_graph_read_port=_FakeKnowledgeService(),
        embedding_client=_UnavailableEmbeddingClient(),
        max_matched=TEST_MAX_MATCHED,
        max_connected=TEST_MAX_CONNECTED,
        vector_candidate_pool_size=TEST_VECTOR_CANDIDATE_POOL_SIZE,
    )

    with pytest.raises(InfrastructureError):
        await service.search("embedding failure raw query")

    record = _search_timing_record(caplog)
    assert record.search_status == "error"
    assert record.search_cache_hit is False
    assert record.search_matched_count == 0
    assert record.search_connected_title_count == 0
    assert "embedding failure raw query" not in caplog.text
    assert all(value != "embedding failure raw query" for value in record.__dict__.values())
