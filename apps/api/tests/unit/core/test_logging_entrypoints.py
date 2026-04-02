"""
Abstract: Unit tests for API and worker entrypoint logging bootstrap ownership.
Out of scope: Handler internals already covered by core logging unit tests.
"""

from __future__ import annotations

from types import SimpleNamespace

import entrypoints.worker.actors as worker_actors
import main as main_module


def _settings(
    *,
    log_level: str = "INFO",
    log_file_path: str = "logs/api/app.log",
    log_file_max_bytes: int = 10_485_760,
    log_file_backup_count: int = 5,
) -> SimpleNamespace:
    return SimpleNamespace(
        log_level=log_level,
        log_file_path=log_file_path,
        log_file_max_bytes=log_file_max_bytes,
        log_file_backup_count=log_file_backup_count,
    )


def test_bootstrap_api_logging_forwards_settings_to_configure() -> None:
    calls: list[dict[str, object]] = []
    fake_settings = _settings()

    def fake_configure_logging(
        *,
        log_level: str,
        log_file_path: str,
        log_file_max_bytes: int,
        log_file_backup_count: int,
    ) -> None:
        calls.append(
            {
                "log_level": log_level,
                "log_file_path": log_file_path,
                "log_file_max_bytes": log_file_max_bytes,
                "log_file_backup_count": log_file_backup_count,
            }
        )

    result = main_module.bootstrap_api_logging(
        settings_loader=lambda: fake_settings,
        configure=fake_configure_logging,
    )

    assert result is fake_settings
    assert calls == [
        {
            "log_level": "INFO",
            "log_file_path": "logs/api/app.log",
            "log_file_max_bytes": 10_485_760,
            "log_file_backup_count": 5,
        }
    ]


def test_build_app_bootstraps_logging_before_app_factory() -> None:
    fake_settings = _settings()
    sentinel_app = object()
    call_order: list[str] = []
    configure_calls: list[dict[str, object]] = []

    def fake_configure_logging(
        *,
        log_level: str,
        log_file_path: str,
        log_file_max_bytes: int,
        log_file_backup_count: int,
    ) -> None:
        call_order.append("configure")
        configure_calls.append(
            {
                "log_level": log_level,
                "log_file_path": log_file_path,
                "log_file_max_bytes": log_file_max_bytes,
                "log_file_backup_count": log_file_backup_count,
            }
        )

    def fake_app_factory() -> object:
        call_order.append("app_factory")
        return sentinel_app

    app = main_module.build_app(
        settings_loader=lambda: fake_settings,
        configure=fake_configure_logging,
        app_factory=fake_app_factory,
    )

    assert app is sentinel_app
    assert call_order == ["configure", "app_factory"]
    assert configure_calls == [
        {
            "log_level": "INFO",
            "log_file_path": "logs/api/app.log",
            "log_file_max_bytes": 10_485_760,
            "log_file_backup_count": 5,
        }
    ]


def test_bootstrap_worker_logging_forwards_settings_to_configure() -> None:
    calls: list[dict[str, object]] = []
    fake_settings = _settings(
        log_level="INFO",
        log_file_path="logs/api/app.log",
        log_file_max_bytes=10_485_760,
        log_file_backup_count=5,
    )

    def fake_configure_logging(
        *,
        log_level: str,
        log_file_path: str,
        log_file_max_bytes: int,
        log_file_backup_count: int,
    ) -> None:
        calls.append(
            {
                "log_level": log_level,
                "log_file_path": log_file_path,
                "log_file_max_bytes": log_file_max_bytes,
                "log_file_backup_count": log_file_backup_count,
            }
        )

    result = worker_actors.bootstrap_worker_logging(
        settings_loader=lambda: fake_settings,
        configure=fake_configure_logging,
    )

    assert result is fake_settings
    assert calls == [
        {
            "log_level": "INFO",
            "log_file_path": "logs/api/app.log",
            "log_file_max_bytes": 10_485_760,
            "log_file_backup_count": 5,
        }
    ]
