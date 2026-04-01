"""CLI messaging and prompt helpers using structured logging."""

from __future__ import annotations

import logging
import sys
from collections.abc import Iterable
from typing import Any

_LOGGER = logging.getLogger("cli")


def _resolve_level(level: int | str, file_obj: Any) -> int:
    """Normalize level inputs and stderr routing."""
    if isinstance(level, str):
        mapping = {
            "debug": logging.DEBUG,
            "info": logging.INFO,
            "warning": logging.WARNING,
            "warn": logging.WARNING,
            "error": logging.ERROR,
            "critical": logging.CRITICAL,
        }
        try:
            return mapping[level.lower()]
        except KeyError as exc:  # pragma: no cover - defensive guard
            raise ValueError(f"Unknown log level: {level}") from exc
    if file_obj is sys.stderr and level == logging.INFO:
        return logging.WARNING
    return level


def cli_echo(
    *values: Any,
    sep: str = " ",
    end: str = "\n",
    level: int | str = logging.INFO,
    file: Any | None = None,
    flush: bool = False,
) -> None:
    """Structured replacement for the builtin ``print``."""
    message = sep.join(str(value) for value in values)
    if end and end != "\n":
        message = f"{message}{end}"
    log_level = _resolve_level(level, file)
    _LOGGER.log(log_level, message)
    if flush:
        for handler in _LOGGER.handlers:
            handler.flush()


def cli_iter(items: Iterable[Any], prefix: str = "", level: int | str = logging.INFO) -> None:
    """Emit each item from ``items`` with an optional ``prefix``."""
    for item in items:
        cli_echo(f"{prefix}{item}", level=level)


def prompt_bool(message: str, default: bool | None = None) -> bool:
    """Prompt the user for a yes/no answer via stdin."""
    suffix = " [y/n]"
    if default is True:
        suffix = " [Y/n]"
    elif default is False:
        suffix = " [y/N]"

    while True:
        try:
            response = input(f"{message}{suffix} ").strip().lower()
        except (EOFError, KeyboardInterrupt):  # pragma: no cover - stdin fallback
            return bool(default)
        if not response and default is not None:
            return default
        if response in {"y", "yes"}:
            return True
        if response in {"n", "no"}:
            return False
        cli_echo("Please respond with 'y' or 'n'.", level=logging.WARNING)


def prompt_text(message: str, default: str | None = None) -> str:
    """Collect free-form text input with an optional default."""
    suffix = f" [{default}]" if default else ""
    try:
        response = input(f"{message}{suffix} ")
    except (EOFError, KeyboardInterrupt):  # pragma: no cover - stdin fallback
        return default or ""
    return response.strip() or (default or "")
