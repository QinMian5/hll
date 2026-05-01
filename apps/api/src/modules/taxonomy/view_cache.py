"""
Abstract: Redis-backed cache helpers for taxonomy view read models.
Out of scope: Taxonomy SQL queries and HTTP response construction.
"""

from __future__ import annotations

import hashlib
import json
from typing import Protocol

from pydantic import TypeAdapter, ValidationError

from modules.taxonomy.dto import TaxonomyLeafLayout
from modules.taxonomy.layout import TAXONOMY_LEAF_LAYOUT_VERSION
from modules.taxonomy.schema import (
    TaxonomyNodeBranchViewResponse,
    TaxonomyNodeLeafViewResponse,
    TaxonomyNodeViewResponse,
    TaxonomyRootViewResponse,
)

TAXONOMY_VIEW_COUNT_CACHE_TTL_SECONDS = 60
TAXONOMY_VIEW_RESPONSE_CACHE_TTL_SECONDS = 60
TAXONOMY_VIEW_LEAF_LAYOUT_CACHE_TTL_SECONDS = 600
TAXONOMY_VIEW_LOCK_TTL_SECONDS = 30
TAXONOMY_VIEW_CACHE_KEY_PREFIX = "taxonomy:view:v1"
TAXONOMY_API_VIEW_CACHE_KEY_PREFIX = "knowledge:api:taxonomy-view:v1"

_NODE_VIEW_ADAPTER = TypeAdapter(TaxonomyNodeViewResponse)


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
    def __init__(
        self,
        *,
        redis: TaxonomyRedisProtocol,
        descendant_count_ttl_seconds: int = TAXONOMY_VIEW_COUNT_CACHE_TTL_SECONDS,
        view_response_ttl_seconds: int = TAXONOMY_VIEW_RESPONSE_CACHE_TTL_SECONDS,
        leaf_layout_ttl_seconds: int = TAXONOMY_VIEW_LEAF_LAYOUT_CACHE_TTL_SECONDS,
    ) -> None:
        self._redis = redis
        self._descendant_count_ttl_seconds = descendant_count_ttl_seconds
        self._view_response_ttl_seconds = view_response_ttl_seconds
        self._leaf_layout_ttl_seconds = leaf_layout_ttl_seconds

    async def get_root_view(self) -> TaxonomyRootViewResponse | None:
        raw_payload = await self._redis.get(_root_view_key())
        if raw_payload is None:
            return None
        payload_text = _payload_text(raw_payload=raw_payload)
        try:
            return TaxonomyRootViewResponse.model_validate_json(payload_text)
        except (ValidationError, ValueError) as exc:
            raise ValueError("Invalid root view cache payload.") from exc

    async def set_root_view(self, view: TaxonomyRootViewResponse) -> None:
        await self._redis.set(
            _root_view_key(),
            _dump_model_payload(view),
            ex=self._view_response_ttl_seconds,
        )

    async def get_node_view(
        self,
        *,
        node_id: int,
    ) -> TaxonomyNodeBranchViewResponse | TaxonomyNodeLeafViewResponse | None:
        raw_payload = await self._redis.get(_node_view_key(node_id=node_id))
        if raw_payload is None:
            return None
        payload_text = _payload_text(raw_payload=raw_payload)
        try:
            return _NODE_VIEW_ADAPTER.validate_json(payload_text)
        except (ValidationError, ValueError) as exc:
            raise ValueError("Invalid node view cache payload.") from exc

    async def set_node_view(
        self,
        *,
        node_id: int,
        view: TaxonomyNodeBranchViewResponse | TaxonomyNodeLeafViewResponse,
    ) -> None:
        await self._redis.set(
            _node_view_key(node_id=node_id),
            _dump_model_payload(view),
            ex=self._view_response_ttl_seconds,
        )

    async def get_path_view(
        self,
        *,
        route_path: str,
    ) -> TaxonomyNodeBranchViewResponse | TaxonomyNodeLeafViewResponse | None:
        raw_payload = await self._redis.get(_path_view_key(route_path=route_path))
        if raw_payload is None:
            return None
        payload_text = _payload_text(raw_payload=raw_payload)
        try:
            return _NODE_VIEW_ADAPTER.validate_json(payload_text)
        except (ValidationError, ValueError) as exc:
            raise ValueError("Invalid path view cache payload.") from exc

    async def set_path_view(
        self,
        *,
        route_path: str,
        view: TaxonomyNodeBranchViewResponse | TaxonomyNodeLeafViewResponse,
    ) -> None:
        await self._redis.set(
            _path_view_key(route_path=route_path),
            _dump_model_payload(view),
            ex=self._view_response_ttl_seconds,
        )

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
            ex=self._descendant_count_ttl_seconds,
        )

    async def acquire_descendant_counts_lock(self) -> bool:
        result = await self._redis.set(
            f"{_descendant_counts_key()}:lock",
            "1",
            ex=TAXONOMY_VIEW_LOCK_TTL_SECONDS,
            nx=True,
        )
        return bool(result)

    async def get_leaf_layout(self, *, leaf_id: int) -> TaxonomyLeafLayout | None:
        raw_payload = await self._redis.get(_leaf_layout_key(leaf_id=leaf_id))
        if raw_payload is None:
            return None
        if isinstance(raw_payload, bytes):
            payload_text = raw_payload.decode("utf-8")
        else:
            payload_text = raw_payload

        try:
            payload = json.loads(payload_text)
            return TaxonomyLeafLayout.model_validate(payload)
        except (json.JSONDecodeError, ValidationError, ValueError) as exc:
            raise ValueError("Invalid leaf layout cache payload.") from exc

    async def set_leaf_layout(self, *, leaf_id: int, layout: TaxonomyLeafLayout) -> None:
        payload = json.dumps(
            layout.model_dump(mode="json"),
            separators=(",", ":"),
            sort_keys=True,
        )
        await self._redis.set(
            _leaf_layout_key(leaf_id=leaf_id),
            payload,
            ex=self._leaf_layout_ttl_seconds,
        )

    async def acquire_leaf_layout_lock(self, *, leaf_id: int) -> bool:
        result = await self._redis.set(
            f"{_leaf_layout_key(leaf_id=leaf_id)}:lock",
            "1",
            ex=TAXONOMY_VIEW_LOCK_TTL_SECONDS,
            nx=True,
        )
        return bool(result)


def _descendant_counts_key() -> str:
    return f"{TAXONOMY_VIEW_CACHE_KEY_PREFIX}:descendant-counts"


def _leaf_layout_key(*, leaf_id: int) -> str:
    return f"{TAXONOMY_VIEW_CACHE_KEY_PREFIX}:leaf-layout:{TAXONOMY_LEAF_LAYOUT_VERSION}:{leaf_id}"


def _root_view_key() -> str:
    return f"{TAXONOMY_API_VIEW_CACHE_KEY_PREFIX}:root"


def _node_view_key(*, node_id: int) -> str:
    return f"{TAXONOMY_API_VIEW_CACHE_KEY_PREFIX}:node:{node_id}"


def _path_view_key(*, route_path: str) -> str:
    digest = hashlib.sha256(route_path.encode("utf-8")).hexdigest()
    return f"{TAXONOMY_API_VIEW_CACHE_KEY_PREFIX}:path:{digest}"


def _payload_text(*, raw_payload: str | bytes) -> str:
    if isinstance(raw_payload, bytes):
        return raw_payload.decode("utf-8")
    return raw_payload


def _dump_model_payload(
    view: TaxonomyRootViewResponse | TaxonomyNodeBranchViewResponse | TaxonomyNodeLeafViewResponse,
) -> str:
    return json.dumps(
        view.model_dump(mode="json"),
        separators=(",", ":"),
        sort_keys=True,
    )
