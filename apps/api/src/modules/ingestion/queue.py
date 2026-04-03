"""
Abstract: Ingestion-owned Dramatiq Redis broker configuration for API and worker
entrypoints.
Out of scope: Knowledge-graph persistence rules and HTTP transport contracts.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import dramatiq
from dramatiq.brokers.redis import RedisBroker
from dramatiq.message import Message

_broker: RedisBroker | None = None
INGESTION_QUEUE_NAME = "ingestion"
INGESTION_ACTOR_NAME = "enqueue_ingestion_task"


@dataclass(slots=True, frozen=True)
class IngestionTask:
    ingestion_id: str
    request_id: str
    title: str
    content: str

    def to_payload(self) -> dict[str, str]:
        return {
            "ingestion_id": self.ingestion_id,
            "request_id": self.request_id,
            "title": self.title,
            "content": self.content,
        }

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> IngestionTask:
        return cls(
            ingestion_id=str(payload["ingestion_id"]),
            request_id=str(payload["request_id"]),
            title=str(payload["title"]),
            content=str(payload["content"]),
        )


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


def publish_ingestion_task(*, redis_url: str, task: IngestionTask) -> Message:
    broker = configure_broker(redis_url=redis_url)
    message = Message(
        queue_name=INGESTION_QUEUE_NAME,
        actor_name=INGESTION_ACTOR_NAME,
        args=(task.to_payload(),),
        kwargs={},
        options={},
    )
    return broker.enqueue(message)
