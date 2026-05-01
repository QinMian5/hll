"""
Abstract: Redis JSON cache primitives for API-owned read models.
Out of scope: Feature cache key semantics and runtime dependency wiring.
"""

from __future__ import annotations

import json
from typing import Protocol, TypeVar

from pydantic import BaseModel, ValidationError

TModel = TypeVar("TModel", bound=BaseModel)


class RedisJsonProtocol(Protocol):
    async def get(self, key: str) -> str | bytes | None: ...

    async def set(
        self,
        key: str,
        value: str,
        *,
        ex: int | None = None,
        nx: bool | None = None,
    ) -> bool | None: ...


class CacheReadError(RuntimeError):
    pass


class CacheWriteError(RuntimeError):
    pass


class CacheDecodeError(ValueError):
    pass


class CacheValidationError(ValueError):
    pass


class JsonRedisCache:
    def __init__(self, *, redis: RedisJsonProtocol) -> None:
        self._redis = redis

    async def get_model(self, *, key: str, model_type: type[TModel]) -> TModel | None:
        try:
            raw_payload = await self._redis.get(key)
        except Exception as exc:
            raise CacheReadError(f"Failed to read cache key {key!r}.") from exc

        if raw_payload is None:
            return None
        if isinstance(raw_payload, bytes):
            payload_text = raw_payload.decode("utf-8")
        else:
            payload_text = raw_payload

        try:
            payload = json.loads(payload_text)
        except json.JSONDecodeError as exc:
            raise CacheDecodeError(f"Failed to decode cache key {key!r}.") from exc

        try:
            return model_type.model_validate(payload)
        except ValidationError as exc:
            raise CacheValidationError(f"Failed to validate cache key {key!r}.") from exc

    async def set_model(self, *, key: str, value: BaseModel, ttl_seconds: int) -> None:
        payload = value.model_dump_json()
        try:
            await self._redis.set(key, payload, ex=ttl_seconds)
        except Exception as exc:
            raise CacheWriteError(f"Failed to write cache key {key!r}.") from exc
