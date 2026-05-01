"""
Abstract: Unit tests for Redis JSON cache serialization and validation.
Out of scope: Redis server integration and feature-owned cache key semantics.
"""

from __future__ import annotations

import pytest
from pydantic import BaseModel, ConfigDict, Field

from shared.cache.json_cache import (
    CacheDecodeError,
    CacheReadError,
    CacheValidationError,
    CacheWriteError,
    JsonRedisCache,
)


class _Payload(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    id: int = Field(gt=0)
    name: str = Field(min_length=1)


class _FakeRedis:
    def __init__(self) -> None:
        self.values: dict[str, str | bytes] = {}
        self.set_calls: list[tuple[str, str, int | None, bool | None]] = []
        self.fail_get = False
        self.fail_set = False

    async def get(self, key: str) -> str | bytes | None:
        if self.fail_get:
            raise RuntimeError("redis get failed")
        return self.values.get(key)

    async def set(
        self,
        key: str,
        value: str,
        *,
        ex: int | None = None,
        nx: bool | None = None,
    ) -> bool:
        if self.fail_set:
            raise RuntimeError("redis set failed")
        self.set_calls.append((key, value, ex, nx))
        self.values[key] = value
        return True


@pytest.mark.anyio
async def test_json_cache_stores_model_payload_with_ttl() -> None:
    redis = _FakeRedis()
    cache = JsonRedisCache(redis=redis)

    await cache.set_model(
        key="cache:key",
        value=_Payload(id=3, name="alpha"),
        ttl_seconds=60,
    )

    assert redis.set_calls == [("cache:key", '{"id":3,"name":"alpha"}', 60, None)]


@pytest.mark.anyio
async def test_json_cache_returns_validated_model_payload() -> None:
    redis = _FakeRedis()
    redis.values["cache:key"] = b'{"id":4,"name":"beta"}'
    cache = JsonRedisCache(redis=redis)

    payload = await cache.get_model(key="cache:key", model_type=_Payload)

    assert payload == _Payload(id=4, name="beta")


@pytest.mark.anyio
async def test_json_cache_returns_none_for_missing_key() -> None:
    cache = JsonRedisCache(redis=_FakeRedis())

    payload = await cache.get_model(key="missing", model_type=_Payload)

    assert payload is None


@pytest.mark.anyio
async def test_json_cache_raises_decode_error_for_malformed_json() -> None:
    redis = _FakeRedis()
    redis.values["cache:key"] = "{bad"
    cache = JsonRedisCache(redis=redis)

    with pytest.raises(CacheDecodeError, match="cache:key"):
        await cache.get_model(key="cache:key", model_type=_Payload)


@pytest.mark.anyio
async def test_json_cache_raises_validation_error_for_malformed_payload() -> None:
    redis = _FakeRedis()
    redis.values["cache:key"] = '{"id":"wrong","name":"beta"}'
    cache = JsonRedisCache(redis=redis)

    with pytest.raises(CacheValidationError, match="cache:key"):
        await cache.get_model(key="cache:key", model_type=_Payload)


@pytest.mark.anyio
async def test_json_cache_wraps_redis_get_failures() -> None:
    redis = _FakeRedis()
    redis.fail_get = True
    cache = JsonRedisCache(redis=redis)

    with pytest.raises(CacheReadError, match="cache:key"):
        await cache.get_model(key="cache:key", model_type=_Payload)


@pytest.mark.anyio
async def test_json_cache_wraps_redis_set_failures() -> None:
    redis = _FakeRedis()
    redis.fail_set = True
    cache = JsonRedisCache(redis=redis)

    with pytest.raises(CacheWriteError, match="cache:key"):
        await cache.set_model(
            key="cache:key",
            value=_Payload(id=3, name="alpha"),
            ttl_seconds=60,
        )
