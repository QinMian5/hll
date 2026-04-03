"""
Abstract: Unit tests for API provider wiring of ingestion service sender dependencies.
Out of scope: HTTP transport behavior and worker-side job execution.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from entrypoints.api import providers as api_providers
from modules.ingestion.queue import IngestionTask
from modules.ingestion.service import IngestionService


@pytest.fixture
def redis_url() -> str:
    return "redis://infra-redis:6379/0"


def test_get_ingestion_service_builds_sender_from_ingestion_queue(
    monkeypatch: pytest.MonkeyPatch,
    redis_url: str,
) -> None:
    captured: dict[str, object] = {}

    def _fake_publish_ingestion_task(
        *,
        redis_url: str,
        task: IngestionTask,
    ) -> None:
        captured["redis_url"] = redis_url
        captured["task"] = task

    monkeypatch.setattr(
        api_providers,
        "publish_ingestion_task",
        _fake_publish_ingestion_task,
    )

    settings = SimpleNamespace(redis_url=redis_url)

    service = api_providers.get_ingestion_service(settings=settings)
    task = IngestionTask(
        ingestion_id="ing_123",
        request_id="req_123",
        title="Title",
        content="Content",
    )
    result = service.task_publisher(task)

    assert isinstance(service, IngestionService)
    assert result is None
    assert captured == {"redis_url": redis_url, "task": task}


def test_provider_module_does_not_export_worker_actor_sender() -> None:
    assert not hasattr(api_providers, "enqueue_ingestion_task")
