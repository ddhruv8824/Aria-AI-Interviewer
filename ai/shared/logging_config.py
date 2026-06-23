"""Loguru configuration shared by the API server and AI services."""

from __future__ import annotations

import sys
from typing import Any

from loguru import logger


def configure_logging(*, level: str = "DEBUG") -> None:
    """Configure structured loguru output for the voice agent process.

    Args:
        level: Minimum log level (DEBUG, INFO, WARNING, ERROR).
    """
    logger.remove()
    logger.add(
        sys.stderr,
        level=level,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{extra[component]}</cyan> | "
            "<level>{message}</level>"
        ),
        filter=lambda record: record["extra"].setdefault("component", "app") or True,
    )


def get_logger(component: str, **bind: Any):
    """Return a logger bound to a logical component name.

    Args:
        component: Short identifier such as ``session`` or ``audio``.
        **bind: Additional structured fields attached to every log line.

    Returns:
        A loguru logger with ``component`` and optional extra fields bound.
    """
    return logger.bind(component=component, **bind)
