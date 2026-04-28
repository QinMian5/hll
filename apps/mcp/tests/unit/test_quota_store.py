"""
Abstract: Unit tests for Redis-backed MCP account quota reservation.
Out of scope: Authentication, usage persistence, and MCP protocol execution.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime, timedelta

import pytest

from knowledge_mcp.quota.store import (
    QuotaInfrastructureError,
    QuotaPolicy,
    QuotaStore,
)


class FakeRedis:
    def __init__(self) -> None:
        self.values: dict[str, int] = {}
        self.ttls: dict[str, int] = {}
        self.seen_keys: list[str] = []

    async def eval(
        self,
        script: str,
        numkeys: int,
        *keys_and_args: object,
    ) -> list[int]:
        assert "INCRBY" in script
        keys = [str(value) for value in keys_and_args[:numkeys]]
        args = [int(str(value)) for value in keys_and_args[numkeys:]]
        cost = args[0]
        limits = args[1:3]
        windows = args[3:5]
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
            retry_after = min(
                self.ttls.get(keys[index], windows[index]) for index, _limit in exceeded
            )
            return [0, retry_after, *remaining]

        for key, value, window in zip(keys, projected, windows, strict=True):
            self.values[key] = value
            self.ttls.setdefault(key, window)
        remaining = [max(limit - value, 0) for value, limit in zip(projected, limits, strict=True)]
        return [1, 0, *remaining]

    async def get(self, key: str) -> str | None:
        value = self.values.get(key)
        if value is None:
            return None
        return str(value)

    async def ttl(self, key: str) -> int:
        return self.ttls.get(key, -2)


class FailingRedis:
    async def eval(self, script: str, numkeys: int, *keys_and_args: object) -> Sequence[int]:
        raise OSError("redis unavailable")

    async def get(self, key: str) -> str | None:
        raise OSError("redis unavailable")

    async def ttl(self, key: str) -> int:
        raise OSError("redis unavailable")


def _policy() -> QuotaPolicy:
    return QuotaPolicy(
        user_daily_limit=2,
        user_daily_window_seconds=86_400,
        user_weekly_limit=10,
        user_weekly_window_seconds=604_800,
    )


@pytest.mark.anyio
async def test_first_reservation_creates_daily_and_weekly_account_keys() -> None:
    store = QuotaStore(redis_client=FakeRedis(), policy=_policy(), clock=lambda: 120.0)

    decision = await store.reserve(
        user_sub="user_123",
        pat_fingerprint="pat_fingerprint",
        cost_units=1,
    )

    assert decision.allowed
    assert decision.remaining == {
        "user_daily": 1,
        "user_weekly": 9,
    }


@pytest.mark.anyio
async def test_second_reservation_increments_active_account_windows() -> None:
    redis = FakeRedis()
    store = QuotaStore(redis_client=redis, policy=_policy(), clock=lambda: 120.0)

    first = await store.reserve(user_sub="user_123", pat_fingerprint="pat_fingerprint")
    second = await store.reserve(user_sub="user_123", pat_fingerprint="pat_fingerprint")

    assert first.allowed
    assert second.allowed
    assert redis.values["knowledge:mcp:quota:user:user_123:daily"] == 2
    assert redis.values["knowledge:mcp:quota:user:user_123:weekly"] == 2


@pytest.mark.anyio
async def test_quota_keys_include_user_but_not_pat_fingerprint_or_raw_pat() -> None:
    redis = FakeRedis()
    store = QuotaStore(redis_client=redis, policy=_policy(), clock=lambda: 120.0)

    await store.reserve(user_sub="user_123", pat_fingerprint="pat_fingerprint")

    assert redis.seen_keys == [
        "knowledge:mcp:quota:user:user_123:daily",
        "knowledge:mcp:quota:user:user_123:weekly",
    ]
    assert all("pat_fingerprint" not in key for key in redis.seen_keys)
    assert all("raw_pat_secret" not in key for key in redis.seen_keys)


@pytest.mark.anyio
async def test_daily_limit_rejects_without_incrementing_weekly_window() -> None:
    redis = FakeRedis()
    redis.values["knowledge:mcp:quota:user:user_123:daily"] = 2
    redis.ttls["knowledge:mcp:quota:user:user_123:daily"] = 123
    redis.values["knowledge:mcp:quota:user:user_123:weekly"] = 2
    redis.ttls["knowledge:mcp:quota:user:user_123:weekly"] = 456
    store = QuotaStore(redis_client=redis, policy=_policy(), clock=lambda: 120.0)

    decision = await store.reserve(user_sub="user_123", pat_fingerprint="pat_fingerprint")

    assert not decision.allowed
    assert decision.retry_after_seconds == 123
    assert redis.values["knowledge:mcp:quota:user:user_123:daily"] == 2
    assert redis.values["knowledge:mcp:quota:user:user_123:weekly"] == 2


@pytest.mark.anyio
async def test_inactive_summary_returns_null_window_timestamps() -> None:
    store = QuotaStore(redis_client=FakeRedis(), policy=_policy(), clock=lambda: 120.0)

    summary = await store.get_summary(user_sub="user_123")

    assert summary.daily.used == 0
    assert summary.daily.remaining == 2
    assert summary.daily.started_at is None
    assert summary.daily.reset_at is None
    assert summary.weekly.used == 0
    assert summary.weekly.remaining == 10
    assert summary.weekly.started_at is None
    assert summary.weekly.reset_at is None


@pytest.mark.anyio
async def test_active_summary_uses_redis_value_and_ttl_for_reset_window() -> None:
    now = datetime(2026, 4, 28, 10, 0, tzinfo=UTC)
    redis = FakeRedis()
    redis.values["knowledge:mcp:quota:user:user_123:daily"] = 1
    redis.ttls["knowledge:mcp:quota:user:user_123:daily"] = 3_600
    redis.values["knowledge:mcp:quota:user:user_123:weekly"] = 3
    redis.ttls["knowledge:mcp:quota:user:user_123:weekly"] = 172_800
    store = QuotaStore(
        redis_client=redis,
        policy=_policy(),
        clock=lambda: now.timestamp(),
    )

    summary = await store.get_summary(user_sub="user_123")

    assert summary.daily.used == 1
    assert summary.daily.remaining == 1
    assert summary.daily.reset_at == now + timedelta(seconds=3_600)
    assert summary.daily.reset_at is not None
    assert summary.daily.started_at == summary.daily.reset_at - timedelta(seconds=86_400)
    assert summary.weekly.used == 3
    assert summary.weekly.remaining == 7
    assert summary.weekly.reset_at == now + timedelta(seconds=172_800)
    assert summary.weekly.reset_at is not None
    assert summary.weekly.started_at == summary.weekly.reset_at - timedelta(seconds=604_800)


@pytest.mark.anyio
async def test_redis_failure_is_dependency_failure_not_fail_open() -> None:
    store = QuotaStore(redis_client=FailingRedis(), policy=_policy(), clock=lambda: 120.0)

    with pytest.raises(QuotaInfrastructureError):
        await store.reserve(user_sub="user_123", pat_fingerprint="pat_fingerprint")
