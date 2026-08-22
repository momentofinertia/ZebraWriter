from __future__ import annotations

import logging
import re
from logging.handlers import RotatingFileHandler
from pathlib import Path


LOG_NAME = "zebrawriter.log"
_SECRET_PATTERNS = (
    re.compile(r"(?i)(authorization\s*[:=]\s*bearer\s+)[^\s,;]+"),
    re.compile(r"(?i)((?:api[_ -]?token|token|password|secret)\s*[:=]\s*)[^\s,;]+"),
)


def redact_text(value: object) -> str:
    output = str(value)
    for pattern in _SECRET_PATTERNS:
        output = pattern.sub(r"\1[REDACTED]", output)
    return output


class RedactingFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        rendered = super().format(record)
        return redact_text(rendered)


def configure_logging(log_directory: Path, *, level: int = logging.INFO) -> Path:
    log_directory.mkdir(parents=True, exist_ok=True)
    log_path = log_directory / LOG_NAME
    handler = RotatingFileHandler(
        log_path,
        maxBytes=1_000_000,
        backupCount=3,
        encoding="utf-8",
    )
    handler.setFormatter(
        RedactingFormatter(
            "%(asctime)s %(levelname)s %(name)s %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S%z",
        )
    )
    root = logging.getLogger()
    for existing in list(root.handlers):
        if getattr(existing, "_zebrawriter_handler", False):
            root.removeHandler(existing)
            existing.close()
    handler._zebrawriter_handler = True  # type: ignore[attr-defined]
    root.addHandler(handler)
    root.setLevel(level)
    return log_path
