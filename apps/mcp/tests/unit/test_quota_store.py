"""
Abstract: Unit tests for Redis-backed MCP quota reservation.
Out of scope: Authentication, usage persistence, and MCP protocol execution.
"""

from __future__ import annotations

from collections.abc import Sequence

import pytest

from knowledge_mcp.quota.store import (
    QuotaInfrastructureError,
    QuotaPolicy,
    QuotaStore,
)


class FakeRedis:
    def __init__(self) -> None:
        self.values: dict[str, int] = {}
        self.seen_keys: list[str] = []

    async def eval(
        self,
        script: str,
        numkeys: int,
        *keys_and_args: object,
    ) -> list[int]:
        assert "INCRBY" in script
        keys = [str(value) for value in keys_and_args[:numkeys]]
        args = [int(value) for value in keys_and_args[numkeys:]]
        cost = args[0]
        limits = args[1:5]
        windows = args[5:9]
        self.seen_keys.extend(keys)

        projected = [self.values.get(key, 0) + cost for key in keys]
        exceeded = [
            (index, limit)
            for index, (value, limit) in enumerate(zip(projected, limits, strict=True))
            if value > limit
        ]
        if exceeded:
            remaining = [
                max(limit - self.values.get(key, 0), 0)
                for key, limit in zip(keys, limits, strict=True)
            ]
            return [0, min(windows), *remaining]

        for key, value in zip(keys, projected, strict=True):
            self.values[key] = value
        remaining = [max(limit - value, 0) for value, limit in zip(projected, limits, strict=True)]
        return [1, 0, *remaining]


class FailingRedis:
    async def eval(self, script: str, numkeys: int, *keys_and_args: object) -> Sequence[int]:
        raise OSError("redis unavailable")


def _policy() -> QuotaPolicy:
    return QuotaPolicy(
        user_burst_limit=2,
        user_burst_window_seconds=60,
        user_total_limit=10,
        user_total_window_seconds=3600,
        pat_burst_limit=1,
        pat_burst_window_seconds=60,
        pat_total_limit=5,
        pat_total_window_seconds=3600,
    )


@pytest.mark.anyio
async def test_successful_reservation_returns_remaining_counters() -> None:
    store = QuotaStore(redis_client=FakeRedis(), policy=_policy(), clock=lambda: 120.0)

    decision = await store.reserve(
        user_sub="user_123",
        pat_fingerprint="pat_fingerprint",
        cost_units=1,
    )

    assert decision.allowed
    assert decision.remaining["user_burst"] == 1
    assert decision.remaining["pat_burst"] == 0


@pytest.mark.anyio
async def test_pat_burst_limit_exceeded_rejects_without_incrementing() -> None:
    redis = FakeRedis()
    store = QuotaStore(redis_client=redis, policy=_policy(), clock=lambda: 120.0)

    first = await store.reserve(user_sub="user_123", pat_fingerprint="pat_fingerprint")
    second = await store.reserve(user_sub="user_123", pat_fingerprint="pat_fingerprint")

    assert first.allowed
    assert not second.allowed
    assert second.retry_after_seconds == 60
    assert redis.values["knowledge:mcp:quota:pat:pat_fingerprint:burst:120"] == 1


@pytest.mark.anyio
async def test_quota_keys_include_user_and_pat_fingerprint_without_raw_pat() -> None:
    redis = FakeRedis()
    store = QuotaStore(redis_client=redis, policy=_policy(), clock=lambda: 120.0)

    await store.reserve(user_sub="user_123", pat_fingerprint="pat_fingerprint")

    assert any(":user:user_123:" in key for key in redis.seen_keys)
    assert any(":pat:pat_fingerprint:" in key for key in redis.seen_keys)
    assert all("raw_pat_secret" not in key for key in redis.seen_keys)


@pytest.mark.anyio
async def test_redis_failure_is_dependency_failure_not_fail_open() -> None:
    store = QuotaStore(redis_client=FailingRedis(), policy=_policy(), clock=lambda: 120.0)

    with pytest.raises(QuotaInfrastructureError):
        await store.reserve(user_sub="user_123", pat_fingerprint="pat_fingerprint")
