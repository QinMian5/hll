"""
Abstract: Redis-backed cache helpers for taxonomy view read models.
Out of scope: Taxonomy SQL queries and HTTP response construction.
"""

from __future__ import annotations

import json
from typing import Protocol

TAXONOMY_VIEW_COUNT_CACHE_TTL_SECONDS = 60
TAXONOMY_VIEW_LOCK_TTL_SECONDS = 30
TAXONOMY_VIEW_CACHE_KEY_PREFIX = "taxonomy:view:v1"


class TaxonomyRedisProtocol(Protocol):
    async def get(self, key: str) -> str | bytes | None: ...

    async def set(
        self,
        key: str,
        value: str,
        *,
        ex: int | None = None,
        nx: bool | None = None,
    ) -> bool | None: ...


class TaxonomyViewRedisCache:
    def __init__(self, *, redis: TaxonomyRedisProtocol) -> None:
        self._redis = redis

    async def get_descendant_counts(self) -> dict[int, int] | None:
        raw_payload = await self._redis.get(_descendant_counts_key())
        if raw_payload is None:
            return None
        if isinstance(raw_payload, bytes):
            payload_text = raw_payload.decode("utf-8")
        else:
            payload_text = raw_payload

        try:
            payload = json.loads(payload_text)
        except json.JSONDecodeError as exc:
            raise ValueError("Invalid descendant count cache payload.") from exc

        counts = payload.get("counts") if isinstance(payload, dict) else None
        if not isinstance(counts, dict):
            raise ValueError("Invalid descendant count cache payload.")

        parsed_counts: dict[int, int] = {}
        for raw_node_id, raw_count in counts.items():
            if not isinstance(raw_node_id, str) or not isinstance(raw_count, int):
                raise ValueError("Invalid descendant count cache payload.")
            parsed_counts[int(raw_node_id)] = raw_count
        return parsed_counts

    async def set_descendant_counts(self, counts: dict[int, int]) -> None:
        normalized_counts = {str(node_id): counts[node_id] for node_id in sorted(counts)}
        payload = json.dumps(
            {"counts": normalized_counts},
            separators=(",", ":"),
        )
        await self._redis.set(
            _descendant_counts_key(),
            payload,
            ex=TAXONOMY_VIEW_COUNT_CACHE_TTL_SECONDS,
        )

    async def acquire_descendant_counts_lock(self) -> bool:
        result = await self._redis.set(
            f"{_descendant_counts_key()}:lock",
            "1",
            ex=TAXONOMY_VIEW_LOCK_TTL_SECONDS,
            nx=True,
        )
        return bool(result)


def _descendant_counts_key() -> str:
    return f"{TAXONOMY_VIEW_CACHE_KEY_PREFIX}:descendant-counts"
