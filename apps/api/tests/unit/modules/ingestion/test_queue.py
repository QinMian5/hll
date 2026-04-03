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


def test_ingestion_task_payload_roundtrip() -> None:
    task = broker_module.IngestionTask(
        ingestion_id="ing_123",
        request_id="req_abc",
        title="Title",
        content="Content",
    )

    payload = task.to_payload()
    rebuilt = broker_module.IngestionTask.from_payload(payload)

    assert rebuilt == task


def test_publish_ingestion_task_enqueues_message_with_fixed_contract(
    monkeypatch: pytest.MonkeyPatch,
    reset_broker_cache: None,
) -> None:
    enqueued_messages: list[_FakeMessage] = []
    created_messages: list[dict[str, object]] = []
    configured_urls: list[str] = []

    class _FakeMessage:
        def __init__(
            self,
            *,
            queue_name: str,
            actor_name: str,
            args: tuple[object, ...],
            kwargs: dict[str, object],
            options: dict[str, object],
        ) -> None:
            created_messages.append(
                {
                    "queue_name": queue_name,
                    "actor_name": actor_name,
                    "args": args,
                    "kwargs": kwargs,
                    "options": options,
                }
            )
            self.args = args

    class _FakeBroker:
        def enqueue(self, message: _FakeMessage) -> _FakeMessage:
            enqueued_messages.append(message)
            return message

    fake_broker = _FakeBroker()

    def _fake_configure_broker(*, redis_url: str) -> _FakeBroker:
        configured_urls.append(redis_url)
        return fake_broker

    monkeypatch.setattr(broker_module, "Message", _FakeMessage)
    monkeypatch.setattr(broker_module, "configure_broker", _fake_configure_broker)

    task = broker_module.IngestionTask(
        ingestion_id="ing_123",
        request_id="req_abc",
        title="Title",
        content="Content",
    )
    result = broker_module.publish_ingestion_task(
        redis_url="redis://infra-redis:6379/0",
        task=task,
    )

    assert len(enqueued_messages) == 1
    assert result is enqueued_messages[0]
    assert configured_urls == ["redis://infra-redis:6379/0"]
    assert len(created_messages) == 1
    assert created_messages[0] == {
        "queue_name": "ingestion",
        "actor_name": "enqueue_ingestion_task",
        "args": (task.to_payload(),),
        "kwargs": {},
        "options": {},
    }
