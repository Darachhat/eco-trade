"""
app/core/logging.py
────────────────────
Structured JSON logging with per-service log files and rotation.
Includes fallback for environments where structlog is not present.
"""

from __future__ import annotations

import logging
import logging.handlers
import os
import sys
from pathlib import Path
from typing import Any

try:
    import structlog
    HAS_STRUCTLOG = True
except ImportError:
    HAS_STRUCTLOG = False

LOG_DIR = Path(os.getenv("LOG_DIR", "logs"))


def _ensure_log_dir() -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)


def _rotating_file_handler(filename: str, level: int = logging.DEBUG) -> logging.Handler:
    _ensure_log_dir()
    handler = logging.handlers.RotatingFileHandler(
        LOG_DIR / filename,
        maxBytes=50 * 1024 * 1024,  # 50 MB
        backupCount=10,
        encoding="utf-8",
    )
    handler.setLevel(level)
    return handler


class _StdlibFallbackLogger:
    """Wrapper around logging.Logger to support structlog-style key=value kwargs."""

    def __init__(self, logger: logging.Logger) -> None:
        self._logger = logger

    def _fmt(self, msg: str, kwargs: dict) -> str:
        if not kwargs:
            return msg
        kw_str = " ".join(f"{k}={v}" for k, v in kwargs.items())
        return f"{msg} | {kw_str}"

    def debug(self, msg: str, *args, **kwargs) -> None:
        self._logger.debug(self._fmt(msg, kwargs), *args)

    def info(self, msg: str, *args, **kwargs) -> None:
        self._logger.info(self._fmt(msg, kwargs), *args)

    def warning(self, msg: str, *args, **kwargs) -> None:
        self._logger.warning(self._fmt(msg, kwargs), *args)

    def error(self, msg: str, *args, **kwargs) -> None:
        self._logger.error(self._fmt(msg, kwargs), *args)

    def critical(self, msg: str, *args, **kwargs) -> None:
        self._logger.critical(self._fmt(msg, kwargs), *args)


def configure_logging(log_level: str = "INFO", service: str = "app") -> None:
    """
    Configure structured logging with JSON output for production and
    pretty-print console output for development.
    """
    _ensure_log_dir()
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    root_logger.handlers.clear()

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    root_logger.addHandler(console_handler)

    _service_files: dict[str, str] = {
        "app": "app.log",
        "market": "market.log",
        "worker": "worker.log",
        "model": "model.log",
        "trading": "trading.log",
        "telegram": "telegram.log",
    }

    for svc, fname in _service_files.items():
        file_handler = _rotating_file_handler(fname)
        lgr = logging.getLogger(svc)
        lgr.addHandler(file_handler)
        lgr.setLevel(numeric_level)

    error_handler = _rotating_file_handler("error.log", level=logging.ERROR)
    root_logger.addHandler(error_handler)

    if HAS_STRUCTLOG:
        shared_processors: list[Any] = [
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.StackInfoRenderer(),
        ]

        is_development = os.getenv("APP_ENV", "development") == "development"
        renderer = structlog.dev.ConsoleRenderer() if is_development else structlog.processors.JSONRenderer()

        structlog.configure(
            processors=[
                *shared_processors,
                structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
            ],
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=True,
        )

        formatter = structlog.stdlib.ProcessorFormatter(
            processor=renderer,
            foreign_pre_chain=shared_processors,
        )

        for handler in root_logger.handlers:
            handler.setFormatter(formatter)
    else:
        fmt = logging.Formatter("[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s")
        for handler in root_logger.handlers:
            handler.setFormatter(fmt)


def get_logger(name: str = "app") -> Any:
    """Return a structured logger for the given service name."""
    if HAS_STRUCTLOG:
        return structlog.get_logger(name)
    return _StdlibFallbackLogger(logging.getLogger(name))
