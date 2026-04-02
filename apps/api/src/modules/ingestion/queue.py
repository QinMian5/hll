"""
Abstract: Ingestion-owned Dramatiq Redis broker configuration for API and worker
entrypoints.
Out of scope: Knowledge-graph persistence rules and HTTP transport contracts.
"""

from __future__ import annotations

import dramatiq
from dramatiq.brokers.redis import RedisBroker

_broker: RedisBroker | None = None


def get_broker(*, redis_url: str) -> RedisBroker:
    global _broker
    if _broker is None:
        _broker = RedisBroker(url=redis_url)
    return _broker


def configure_broker(*, redis_url: str) -> RedisBroker:
    broker = get_broker(redis_url=redis_url)
    if dramatiq.get_broker() is not broker:
        dramatiq.set_broker(broker)
    return broker
