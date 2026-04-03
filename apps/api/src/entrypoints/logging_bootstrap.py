"""
Abstract: Shared process logging bootstrap contract for API and worker entrypoints.
Out of scope: HTTP app factory wiring and worker actor registration behavior.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol

from core.logging import configure_logging
from entrypoints.runtime import get_settings


class LoggingSettings(Protocol):
    log_level: str
    log_file_path: str
    log_file_max_bytes: int
    log_file_backup_count: int


class ConfigureLogging(Protocol):
    def __call__(
        self,
        *,
        log_level: str,
        log_file_path: str,
        log_file_max_bytes: int,
        log_file_backup_count: int,
    ) -> None: ...


def bootstrap_logging(
    *,
    settings_loader: Callable[[], LoggingSettings] = get_settings,
    configure: ConfigureLogging = configure_logging,
) -> LoggingSettings:
    settings = settings_loader()
    configure(
        log_level=settings.log_level,
        log_file_path=settings.log_file_path,
        log_file_max_bytes=settings.log_file_max_bytes,
        log_file_backup_count=settings.log_file_backup_count,
    )
    return settings


__all__ = ["ConfigureLogging", "LoggingSettings", "bootstrap_logging"]
