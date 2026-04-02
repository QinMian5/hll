"""
Abstract: Integration smoke test for Redis reachability in isolated test runtime.
Out of scope: Queue retry policy and worker orchestration correctness.
"""

from __future__ import annotations

import pytest
from redis.asyncio import Redis

from core.config import Settings


@pytest.mark.anyio
@pytest.mark.integration
@pytest.mark.db
async def test_redis_ping_succeeds(test_settings: Settings) -> None:
    client = Redis.from_url(
        test_settings.redis_url,
        decode_responses=True,
    )
    try:
        assert await client.ping() is True
    finally:
        await client.aclose()
