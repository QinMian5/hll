"""
Abstract: Unit tests for process-level logging bootstrap behavior.
Out of scope: FastAPI exception handling semantics and request-scoped
context propagation.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Iterator
from logging.handlers import RotatingFileHandler
from pathlib import Path

import pytest

import core.logging as logging_module


@pytest.fixture(autouse=True)
def restore_root_logger() -> Iterator[None]:
    root_logger = logging.getLogger()
    original_handlers = list(root_logger.handlers)
    original_level = root_logger.level

    try:
        yield
    finally:
        for handler in list(root_logger.handlers):
            root_logger.removeHandler(handler)
        root_logger.setLevel(original_level)
        for handler in original_handlers:
            if handler not in root_logger.handlers:
                root_logger.addHandler(handler)


def test_configure_logging_sets_root_handlers_and_applies_config(
    tmp_path: Path,
) -> None:
    log_file_path = tmp_path / "logs" / "app.log"

    logging_module.configure_logging(
        log_level="DEBUG",
        log_file_path=str(log_file_path),
        log_file_max_bytes=1234,
        log_file_backup_count=7,
    )

    root_logger = logging.getLogger()
    assert root_logger.level == logging.DEBUG
    assert len(root_logger.handlers) == 2

    file_handler = next(
        handler
        for handler in root_logger.handlers
        if isinstance(handler, RotatingFileHandler)
    )
    assert file_handler.maxBytes == 1234
    assert file_handler.backupCount == 7
    assert file_handler.baseFilename == str(log_file_path.resolve())

    stream_handler = next(
        handler
        for handler in root_logger.handlers
        if isinstance(handler, logging.StreamHandler)
        and not isinstance(handler, RotatingFileHandler)
    )
    assert stream_handler.formatter is not None


def test_configure_logging_replaces_preexisting_handlers_and_is_idempotent(
    tmp_path: Path,
) -> None:
    root_logger = logging.getLogger()
    sentinel_handler = logging.NullHandler()
    root_logger.addHandler(sentinel_handler)

    logging_module.configure_logging(
        log_level="INFO",
        log_file_path=str(tmp_path / "logs" / "app.log"),
        log_file_max_bytes=1024,
        log_file_backup_count=2,
    )
    assert sentinel_handler not in root_logger.handlers
    assert len(root_logger.handlers) == 2

    logging_module.configure_logging(
        log_level="INFO",
        log_file_path=str(tmp_path / "logs" / "app.log"),
        log_file_max_bytes=1024,
        log_file_backup_count=2,
    )
    assert len(root_logger.handlers) == 2


def test_configure_logging_formatter_outputs_expected_fields(tmp_path: Path) -> None:
    log_file_path = tmp_path / "logs" / "app.log"
    logging_module.configure_logging(
        log_level="INFO",
        log_file_path=str(log_file_path),
        log_file_max_bytes=1024,
        log_file_backup_count=2,
    )

    logger = logging_module.get_logger("unit.formatter")
    logger.info("formatter smoke")

    line = log_file_path.read_text(encoding="utf-8").strip().splitlines()[-1]
    assert "INFO" in line
    assert "unit.formatter" in line
    assert "formatter smoke" in line
    assert re.search(r"\d{4}-\d{2}-\d{2}", line)


def test_get_logger_returns_named_logger() -> None:
    logger = logging_module.get_logger("modules.ingestion.service")
    assert logger.name == "modules.ingestion.service"
    assert logger.propagate is True


def test_configure_logging_creates_parent_directory_when_missing(
    tmp_path: Path,
) -> None:
    log_file_path = tmp_path / "missing" / "nested" / "app.log"
    assert not log_file_path.parent.exists()

    logging_module.configure_logging(
        log_level="INFO",
        log_file_path=str(log_file_path),
        log_file_max_bytes=1024,
        log_file_backup_count=2,
    )
    assert log_file_path.parent.exists()


def test_configure_logging_fails_when_parent_is_not_directory(tmp_path: Path) -> None:
    non_directory_parent = tmp_path / "not_a_directory"
    non_directory_parent.write_text("x", encoding="utf-8")
    log_file_path = non_directory_parent / "app.log"

    with pytest.raises(NotADirectoryError):
        logging_module.configure_logging(
            log_level="INFO",
            log_file_path=str(log_file_path),
            log_file_max_bytes=1024,
            log_file_backup_count=2,
        )


def test_configure_logging_fails_when_parent_directory_creation_errors(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    log_file_path = tmp_path / "blocked" / "app.log"

    def fake_create_directory(path: Path) -> None:
        if path == log_file_path.parent:
            raise PermissionError("blocked mkdir")

    monkeypatch.setattr(logging_module, "_create_directory", fake_create_directory)

    with pytest.raises(PermissionError, match="blocked mkdir"):
        logging_module.configure_logging(
            log_level="INFO",
            log_file_path=str(log_file_path),
            log_file_max_bytes=1024,
            log_file_backup_count=2,
        )


def test_configure_logging_fails_when_parent_directory_not_writable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    log_directory = tmp_path / "readonly"
    log_directory.mkdir()
    log_file_path = log_directory / "app.log"

    def fake_is_writable_directory(path: Path) -> bool:
        return path != log_directory

    monkeypatch.setattr(
        logging_module, "_is_writable_directory", fake_is_writable_directory
    )

    with pytest.raises(PermissionError, match="not writable"):
        logging_module.configure_logging(
            log_level="INFO",
            log_file_path=str(log_file_path),
            log_file_max_bytes=1024,
            log_file_backup_count=2,
        )
