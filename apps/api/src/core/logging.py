"""
Abstract: Process-level logging bootstrap and module logger retrieval helpers.
Out of scope: Request correlation propagation and external log shipping integration.
"""

from __future__ import annotations

import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path

_DEFAULT_FORMAT = "%(asctime)s %(levelname)s %(name)s %(message)s"
_HANDLER_MARKER = "_knowledge_logging_managed"


def _resolve_log_level(log_level: str) -> int:
    normalized = log_level.strip().upper()
    level_value = getattr(logging, normalized, None)
    if not isinstance(level_value, int):
        raise ValueError(f"Unsupported log level: {log_level!r}")
    return level_value


def _create_directory(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def _is_writable_directory(path: Path) -> bool:
    return os.access(path, os.W_OK)


def _prepare_log_path(log_file_path: str) -> Path:
    path = Path(log_file_path)
    parent = path.parent

    if parent.exists() and not parent.is_dir():
        raise NotADirectoryError(f"Log directory is not a directory: {parent}")

    if not parent.exists():
        _create_directory(parent)

    if not _is_writable_directory(parent):
        raise PermissionError(f"Log directory is not writable: {parent}")

    if path.exists() and path.is_dir():
        raise IsADirectoryError(f"Log file path points to a directory: {path}")

    return path


def _replace_root_handlers(*, root_logger: logging.Logger) -> None:
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)
        if getattr(handler, _HANDLER_MARKER, False):
            handler.close()


def configure_logging(
    *,
    log_level: str,
    log_file_path: str,
    log_file_max_bytes: int,
    log_file_backup_count: int,
) -> None:
    root_logger = logging.getLogger()
    _replace_root_handlers(root_logger=root_logger)

    resolved_path = _prepare_log_path(log_file_path)
    resolved_level = _resolve_log_level(log_level)
    formatter = logging.Formatter(_DEFAULT_FORMAT)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    setattr(console_handler, _HANDLER_MARKER, True)

    file_handler = RotatingFileHandler(
        resolved_path,
        maxBytes=log_file_max_bytes,
        backupCount=log_file_backup_count,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    setattr(file_handler, _HANDLER_MARKER, True)

    root_logger.setLevel(resolved_level)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
