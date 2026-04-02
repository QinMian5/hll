"""
Abstract: API process bootstrap that initializes logging and exports the app entrypoint.
Out of scope: Route registration details and request-scoped dependency behavior.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol

from core.logging import configure_logging
from entrypoints.api.app import create_app
from entrypoints.runtime import get_settings


class _LoggingSettings(Protocol):
    log_level: str
    log_file_path: str
    log_file_max_bytes: int
    log_file_backup_count: int


class _ConfigureLogging(Protocol):
    def __call__(
        self,
        *,
        log_level: str,
        log_file_path: str,
        log_file_max_bytes: int,
        log_file_backup_count: int,
    ) -> None: ...


class _AppFactory(Protocol):
    def __call__(self) -> object: ...


def bootstrap_api_logging(
    *,
    settings_loader: Callable[[], _LoggingSettings] = get_settings,
    configure: _ConfigureLogging = configure_logging,
) -> _LoggingSettings:
    settings = settings_loader()
    configure(
        log_level=settings.log_level,
        log_file_path=settings.log_file_path,
        log_file_max_bytes=settings.log_file_max_bytes,
        log_file_backup_count=settings.log_file_backup_count,
    )
    return settings


def build_app(
    *,
    settings_loader: Callable[[], _LoggingSettings] = get_settings,
    configure: _ConfigureLogging = configure_logging,
    app_factory: _AppFactory = create_app,
) -> object:
    bootstrap_api_logging(settings_loader=settings_loader, configure=configure)
    return app_factory()


app = build_app()

__all__ = ["app"]
