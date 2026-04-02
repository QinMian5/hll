"""
Abstract: Unit tests for ingestion-owned Dramatiq broker settings resolution behavior.
Out of scope: Redis network connectivity and worker process lifecycle behavior.
"""

from __future__ import annotations

import pytest

import modules.ingestion.queue as broker_module


@pytest.fixture
def reset_broker_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(broker_module, "_broker", None)


def test_get_broker_uses_settings_redis_url(
    monkeypatch: pytest.MonkeyPatch,
    reset_broker_cache: None,
) -> None:
    class _FakeRedisBroker:
        def __init__(self, *, url: str) -> None:
            self.url = url

    monkeypatch.setattr(
        broker_module,
        "RedisBroker",
        _FakeRedisBroker,
    )

    broker = broker_module.get_broker(redis_url="redis://infra-redis:6379/0")

    assert isinstance(broker, _FakeRedisBroker)
    assert broker.url == "redis://infra-redis:6379/0"


def test_get_broker_raises_when_broker_construction_fails(
    monkeypatch: pytest.MonkeyPatch,
    reset_broker_cache: None,
) -> None:
    def _raise_broker_unavailable(**_: object) -> None:
        raise RuntimeError("broker unavailable")

    monkeypatch.setattr(
        broker_module,
        "RedisBroker",
        _raise_broker_unavailable,
    )

    with pytest.raises(RuntimeError, match="broker unavailable"):
        broker_module.get_broker(redis_url="redis://infra-redis:6379/0")

    assert broker_module._broker is None
