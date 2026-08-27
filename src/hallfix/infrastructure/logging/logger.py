"""Structured JSON-lines logging with mandatory redaction.

Every record written to the log file goes through ``RedactingFilter`` —
there is no code path that writes an unredacted record, since the filter is
attached to the handler itself rather than left as something call sites
must remember to apply.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from hallfix.infrastructure.logging.redaction import redact_mapping, redact_text
from hallfix.utils.paths import log_dir

_LOGGER_NAME = "hallfix"
_STANDARD_ATTRS = frozenset(logging.LogRecord("", 0, "", 0, "", (), None).__dict__.keys())


class RedactingFilter(logging.Filter):
    """Redacts the formatted message and any structured ``extra`` fields."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = redact_text(str(record.msg))
        record.args = ()
        extras = {k: v for k, v in record.__dict__.items() if k not in _STANDARD_ATTRS}
        if extras:
            for key, value in redact_mapping(extras).items():
                setattr(record, key, value)
        return True


class JSONLinesFormatter(logging.Formatter):
    """Formats each record as one JSON object per line."""

    def format(self, record: logging.LogRecord) -> str:
        extras = {
            k: v
            for k, v in record.__dict__.items()
            if k not in _STANDARD_ATTRS and not k.startswith("_")
        }
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            **extras,
        }
        if record.exc_info:
            payload["error"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str, sort_keys=True)


def setup_logging(
    *,
    verbose: bool = False,
    quiet: bool = False,
    log_directory: Path | None = None,
) -> logging.Logger:
    """Configure and return the ``hallfix`` logger.

    Idempotent: safe to call multiple times (e.g. once per CLI invocation)
    without stacking duplicate handlers.
    """
    logger = logging.getLogger(_LOGGER_NAME)
    logger.handlers.clear()
    logger.setLevel(logging.DEBUG)
    logger.propagate = False

    directory = log_directory or log_dir()
    directory.mkdir(parents=True, exist_ok=True)
    file_handler = logging.FileHandler(directory / "hallfix.log", encoding="utf-8")
    file_handler.setFormatter(JSONLinesFormatter())
    file_handler.addFilter(RedactingFilter())
    file_handler.setLevel(logging.DEBUG)
    logger.addHandler(file_handler)

    if not quiet:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
        console_handler.addFilter(RedactingFilter())
        console_handler.setLevel(logging.DEBUG if verbose else logging.WARNING)
        logger.addHandler(console_handler)

    return logger


def get_logger() -> logging.Logger:
    """Return the Hallfix logger, configuring it with defaults if needed."""
    logger = logging.getLogger(_LOGGER_NAME)
    if not logger.handlers:
        return setup_logging()
    return logger
