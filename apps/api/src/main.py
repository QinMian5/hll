"""
Abstract: API process bootstrap that initializes logging and exports the app entrypoint.
Out of scope: Route registration details and request-scoped dependency behavior.
"""

from __future__ import annotations

from collections.abc import Callable

from fastapi import FastAPI

from core.logging import configure_logging
from entrypoints.api.app import create_app
from entrypoints.logging_bootstrap import (
    ConfigureLogging,
    LoggingSettings,
    bootstrap_logging,
)
from entrypoints.runtime import get_settings


def bootstrap_api_logging(
    *,
    settings_loader: Callable[[], LoggingSettings] = get_settings,
    configure: ConfigureLogging = configure_logging,
) -> LoggingSettings:
    return bootstrap_logging(
        settings_loader=settings_loader,
        configure=configure,
    )


def build_app(
    *,
    settings_loader: Callable[[], LoggingSettings] = get_settings,
    configure: ConfigureLogging = configure_logging,
    app_factory: Callable[[], FastAPI] = create_app,
) -> FastAPI:
    bootstrap_api_logging(settings_loader=settings_loader, configure=configure)
    return app_factory()


app = build_app()

__all__ = ["app"]
