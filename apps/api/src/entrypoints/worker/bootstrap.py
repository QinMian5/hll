"""
Abstract: Worker process bootstrap functions that initialize logging and configure the broker.
Out of scope: Actor runtime business logic and queue payload semantics.
"""

from __future__ import annotations

from collections.abc import Callable
from importlib import import_module
from typing import Protocol

from core.logging import configure_logging
from entrypoints.logging_bootstrap import (
    ConfigureLogging,
    LoggingSettings,
    bootstrap_logging,
)
from entrypoints.runtime import get_settings
from modules.ingestion.queue import configure_broker


class WorkerBootstrapSettings(LoggingSettings, Protocol):
    redis_url: str


def bootstrap_worker_logging(
    *,
    settings_loader: Callable[[], LoggingSettings] = get_settings,
    configure: ConfigureLogging = configure_logging,
) -> LoggingSettings:
    return bootstrap_logging(
        settings_loader=settings_loader,
        configure=configure,
    )


def import_worker_actors() -> None:
    import_module("entrypoints.worker.actors")


def _configure_worker_broker(redis_url: str) -> None:
    configure_broker(redis_url=redis_url)


def bootstrap_worker(
    *,
    settings_loader: Callable[[], WorkerBootstrapSettings] = get_settings,
    configure: ConfigureLogging = configure_logging,
    broker_configure: Callable[[str], None] = _configure_worker_broker,
    actor_importer: Callable[[], None] = import_worker_actors,
) -> WorkerBootstrapSettings:
    settings = settings_loader()
    bootstrap_worker_logging(settings_loader=lambda: settings, configure=configure)
    broker_configure(settings.redis_url)
    actor_importer()
    return settings


__all__ = [
    "WorkerBootstrapSettings",
    "bootstrap_worker",
    "bootstrap_worker_logging",
    "import_worker_actors",
]
