"""
Abstract: Redis-backed account quota reservation for MCP search calls.
Out of scope: Authentication, durable usage ledgers, and product pricing policy.
"""

from __future__ import annotations

import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Protocol

RESERVE_SCRIPT = """
local cost = tonumber(ARGV[1])
local retry_after = nil
local remaining = {}

for i = 1, 2 do
  local current = tonumber(redis.call("GET", KEYS[i]) or "0")
  local limit = tonumber(ARGV[i + 1])
  local window_seconds = tonumber(ARGV[i + 3])
  if current + cost > limit then
    local ttl = tonumber(redis.call("TTL", KEYS[i]))
    if ttl == nil or ttl < 1 then
      ttl = window_seconds
    end
    if retry_after == nil or ttl < retry_after then
      retry_after = ttl
    end
  end
  remaining[i] = math.max(limit - current, 0)
end

if retry_after ~= nil then
  return {0, retry_after, remaining[1], remaining[2]}
end

for i = 1, 2 do
  local value = redis.call("INCRBY", KEYS[i], cost)
  local limit = tonumber(ARGV[i + 1])
  local window_seconds = tonumber(ARGV[i + 3])
  if value == cost then
    redis.call("EXPIRE", KEYS[i], window_seconds)
  end
  remaining[i] = math.max(limit - value, 0)
end

return {1, 0, remaining[1], remaining[2]}
"""


class RedisEvalClient(Protocol):
    async def eval(self, script: str, numkeys: int, *keys_and_args: object) -> object: ...

    async def get(self, key: str) -> object: ...

    async def ttl(self, key: str) -> int: ...


class QuotaInfrastructureError(RuntimeError):
    pass


@dataclass(frozen=True)
class QuotaPolicy:
    user_daily_limit: int
    user_daily_window_seconds: int
    user_weekly_limit: int
    user_weekly_window_seconds: int


@dataclass(frozen=True)
class QuotaDecision:
    allowed: bool
    retry_after_seconds: int
    remaining: dict[str, int]


@dataclass(frozen=True)
class QuotaWindowSnapshot:
    used: int
    limit: int
    remaining: int
    window_seconds: int
    started_at: datetime | None
    reset_at: datetime | None

    @classmethod
    def inactive(cls, *, limit: int, window_seconds: int) -> QuotaWindowSnapshot:
        return cls(
            used=0,
            limit=limit,
            remaining=limit,
            window_seconds=window_seconds,
            started_at=None,
            reset_at=None,
        )


@dataclass(frozen=True)
class QuotaSummary:
    daily: QuotaWindowSnapshot
    weekly: QuotaWindowSnapshot


class QuotaStore:
    def __init__(
        self,
        *,
        redis_client: RedisEvalClient,
        policy: QuotaPolicy,
        prefix: str = "knowledge:mcp:quota:",
        clock: Callable[[], float] = time.time,
    ) -> None:
        self._redis_client = redis_client
        self._policy = policy
        self._prefix = prefix
        self._clock = clock

    async def reserve(
        self,
        *,
        user_sub: str,
        pat_fingerprint: str,
        cost_units: int = 1,
    ) -> QuotaDecision:
        if cost_units < 1:
            raise ValueError("cost_units must be greater than or equal to 1.")

        keys = self._keys(user_sub=user_sub)
        limits = (
            self._policy.user_daily_limit,
            self._policy.user_weekly_limit,
        )
        windows = (
            self._policy.user_daily_window_seconds,
            self._policy.user_weekly_window_seconds,
        )
        try:
            raw_result = await self._redis_client.eval(
                RESERVE_SCRIPT,
                len(keys),
                *keys,
                cost_units,
                *limits,
                *windows,
            )
        except (OSError, RuntimeError, ValueError) as exc:
            raise QuotaInfrastructureError("Quota reservation failed.") from exc

        result = self._parse_result(raw_result)
        return QuotaDecision(
            allowed=result[0] == 1,
            retry_after_seconds=result[1],
            remaining={
                "user_daily": result[2],
                "user_weekly": result[3],
            },
        )

    async def get_summary(self, *, user_sub: str) -> QuotaSummary:
        keys = self._keys(user_sub=user_sub)
        daily = await self._window_snapshot(
            key=keys[0],
            limit=self._policy.user_daily_limit,
            window_seconds=self._policy.user_daily_window_seconds,
        )
        weekly = await self._window_snapshot(
            key=keys[1],
            limit=self._policy.user_weekly_limit,
            window_seconds=self._policy.user_weekly_window_seconds,
        )
        return QuotaSummary(daily=daily, weekly=weekly)

    def _keys(self, *, user_sub: str) -> tuple[str, str]:
        return (
            f"{self._prefix}user:{user_sub}:daily",
            f"{self._prefix}user:{user_sub}:weekly",
        )

    async def _window_snapshot(
        self,
        *,
        key: str,
        limit: int,
        window_seconds: int,
    ) -> QuotaWindowSnapshot:
        try:
            raw_value = await self._redis_client.get(key)
            if raw_value is None:
                return QuotaWindowSnapshot.inactive(
                    limit=limit,
                    window_seconds=window_seconds,
                )

            used = _parse_nonnegative_int(raw_value)
            ttl_seconds = int(await self._redis_client.ttl(key))
        except (AttributeError, OSError, RuntimeError, TypeError, ValueError) as exc:
            raise QuotaInfrastructureError("Quota summary read failed.") from exc

        if ttl_seconds < 1:
            raise QuotaInfrastructureError("Quota summary key is missing an expiry.")

        now = datetime.fromtimestamp(self._clock(), UTC)
        reset_at = now + timedelta(seconds=ttl_seconds)
        started_at = reset_at - timedelta(seconds=window_seconds)

        return QuotaWindowSnapshot(
            used=used,
            limit=limit,
            remaining=max(limit - used, 0),
            window_seconds=window_seconds,
            started_at=started_at,
            reset_at=reset_at,
        )

    def _parse_result(self, raw_result: object) -> tuple[int, int, int, int]:
        if not isinstance(raw_result, Sequence) or len(raw_result) != 4:
            raise QuotaInfrastructureError("Quota reservation returned an invalid response.")

        converted: list[int] = []
        try:
            for value in raw_result:
                converted.append(_parse_nonnegative_int(value))
        except (TypeError, ValueError) as exc:
            raise QuotaInfrastructureError(
                "Quota reservation returned non-integer values."
            ) from exc

        return (
            converted[0],
            converted[1],
            converted[2],
            converted[3],
        )


def _parse_nonnegative_int(value: object) -> int:
    if not isinstance(value, (int, str, bytes, bytearray)):
        raise TypeError("Expected integer-like value.")
    parsed = int(value)
    if parsed < 0:
        raise ValueError("Expected non-negative integer.")
    return parsed
