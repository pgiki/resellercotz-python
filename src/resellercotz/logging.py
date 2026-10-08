"""Logging setup for resellercotz-python."""

from __future__ import annotations

import logging

_logger = logging.getLogger("resellercotz")


def set_log_level(level: str) -> None:
    """Set the log level for the ``resellercotz`` logger."""
    _logger.setLevel(getattr(logging, str(level or "INFO").upper(), logging.INFO))


def get_logger(name: str) -> logging.Logger:
    """Child logger under the ``resellercotz`` namespace."""
    return logging.getLogger(f"resellercotz.{name}")
