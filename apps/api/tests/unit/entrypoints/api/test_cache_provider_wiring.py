"""
Abstract: Unit tests for API cache provider wiring.
Out of scope: HTTP route behavior and Redis server integration.
"""

from __future__ import annotations

import inspect
from types import SimpleNamespace

import pytest

from entrypoints.api import providers as api_providers
from modules.search.cache import SearchRedisEmbeddingCache, SearchRedisResponseCache
from modules.taxonomy.view_cache import TaxonomyViewRedisCache


def _settings() -> SimpleNamespace:
    return SimpleNamespace(
        redis_url="redis://cache-redis:6379/0",
        search_max_matched=3,
        search_max_connected=7,
        search_response_cache_ttl_seconds=60,
        search_embedding_cache_ttl_seconds=86400,
        embedding_model="text-embedding-3-small",
        taxonomy_view_cache_ttl_seconds=60,
        taxonomy_leaf_layout_cache_ttl_seconds=600,
    )


@pytest.fixture
def redis_from_url_calls(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    calls: list[str] = []

    def _fake_from_url(redis_url: str) -> object:
        calls.append(redis_url)
        return object()

    monkeypatch.setattr(api_providers.Redis, "from_url", staticmethod(_fake_from_url))
    return calls


def test_get_search_service_wires_response_and_embedding_caches_from_settings_redis_url(
    redis_from_url_calls: list[str],
) -> None:
    service = api_providers.get_search_service(
        knowledge_graph_read_port=object(),
        embedding_client=object(),
        settings=_settings(),
    )

    assert isinstance(service._response_cache, SearchRedisResponseCache)
    assert isinstance(service._embedding_cache, SearchRedisEmbeddingCache)
    assert service._embedding_model == "text-embedding-3-small"
    assert redis_from_url_calls == [
        "redis://cache-redis:6379/0",
        "redis://cache-redis:6379/0",
    ]


def test_get_taxonomy_service_wires_view_cache_from_settings_redis_url(
    redis_from_url_calls: list[str],
) -> None:
    service = api_providers.get_taxonomy_service(
        session=object(),
        knowledge_projection_port=object(),
        settings=_settings(),
    )

    assert isinstance(service._view_cache, TaxonomyViewRedisCache)
    assert redis_from_url_calls == ["redis://cache-redis:6379/0"]


def test_api_providers_do_not_read_redis_configuration_from_process_environment() -> None:
    source = inspect.getsource(api_providers)

    assert "os.environ" not in source
    assert "getenv" not in source
