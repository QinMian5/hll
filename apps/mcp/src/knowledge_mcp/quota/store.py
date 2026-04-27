"""
Abstract: Redis-backed quota reservation for MCP user and PAT-fingerprint limits.
Out of scope: Authentication, durable usage ledgers, and product pricing policy.
"""

from __future__ import annotations

import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Protocol

RESERVE_SCRIPT = """
local cost = tonumber(ARGV[1])
local retry_after = nil
local remaining = {}

for i = 1, 4 do
  local current = tonumber(redis.call("GET", KEYS[i]) or "0")
  local limit = tonumber(ARGV[i + 1])
  local window_seconds = tonumber(ARGV[i + 5])
  if current + cost > limit then
    if retry_after == nil or window_seconds < retry_after then
      retry_after = window_seconds
    end
  end
  remaining[i] = math.max(limit - current, 0)
end

if retry_after ~= nil then
  return {0, retry_after, remaining[1], remaining[2], remaining[3], remaining[4]}
end

for i = 1, 4 do
  local value = redis.call("INCRBY", KEYS[i], cost)
  local limit = tonumber(ARGV[i + 1])
  local window_seconds = tonumber(ARGV[i + 5])
  if value == cost then
    redis.call("EXPIRE", KEYS[i], window_seconds)
  end
  remaining[i] = math.max(limit - value, 0)
end

return {1, 0, remaining[1], remaining[2], remaining[3], remaining[4]}
"""


class RedisEvalClient(Protocol):
    async def eval(self, script: str, numkeys: int, *keys_and_args: object) -> object: ...


class QuotaInfrastructureError(RuntimeError):
    pass


@dataclass(frozen=True)
class QuotaPolicy:
    user_burst_limit: int
    user_burst_window_seconds: int
    user_total_limit: int
    user_total_window_seconds: int
    pat_burst_limit: int
    pat_burst_window_seconds: int
    pat_total_limit: int
    pat_total_window_seconds: int


@dataclass(frozen=True)
class QuotaDecision:
    allowed: bool
    retry_after_seconds: int
    remaining: dict[str, int]


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

        keys = self._keys(user_sub=user_sub, pat_fingerprint=pat_fingerprint)
        limits = (
            self._policy.user_burst_limit,
            self._policy.user_total_limit,
            self._policy.pat_burst_limit,
            self._policy.pat_total_limit,
        )
        windows = (
            self._policy.user_burst_window_seconds,
            self._policy.user_total_window_seconds,
            self._policy.pat_burst_window_seconds,
            self._policy.pat_total_window_seconds,
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
                "user_burst": result[2],
                "user_total": result[3],
                "pat_burst": result[4],
                "pat_total": result[5],
            },
        )

    def _keys(self, *, user_sub: str, pat_fingerprint: str) -> tuple[str, str, str, str]:
        now = int(self._clock())
        user_burst_start = _window_start(now, self._policy.user_burst_window_seconds)
        user_total_start = _window_start(now, self._policy.user_total_window_seconds)
        pat_burst_start = _window_start(now, self._policy.pat_burst_window_seconds)
        pat_total_start = _window_start(now, self._policy.pat_total_window_seconds)

        return (
            f"{self._prefix}user:{user_sub}:burst:{user_burst_start}",
            f"{self._prefix}user:{user_sub}:total:{user_total_start}",
            f"{self._prefix}pat:{pat_fingerprint}:burst:{pat_burst_start}",
            f"{self._prefix}pat:{pat_fingerprint}:total:{pat_total_start}",
        )

    def _parse_result(self, raw_result: object) -> tuple[int, int, int, int, int, int]:
        if not isinstance(raw_result, Sequence) or len(raw_result) != 6:
            raise QuotaInfrastructureError("Quota reservation returned an invalid response.")

        converted: list[int] = []
        try:
            for value in raw_result:
                if not isinstance(value, (int, str, bytes, bytearray)):
                    raise TypeError
                converted.append(int(value))
        except (TypeError, ValueError) as exc:
            raise QuotaInfrastructureError(
                "Quota reservation returned non-integer values."
            ) from exc

        return (
            converted[0],
            converted[1],
            converted[2],
            converted[3],
            converted[4],
            converted[5],
        )


def _window_start(timestamp_seconds: int, window_seconds: int) -> int:
    return timestamp_seconds - (timestamp_seconds % window_seconds)
