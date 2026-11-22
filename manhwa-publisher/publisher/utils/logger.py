"""Structured logging with secret redaction and JSON-mode stream routing."""

from __future__ import annotations

import json
import logging
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_SECRET_PATTERNS = [
    re.compile(r"(Bearer\s+)([A-Za-z0-9\-._~+/]+=*)", re.IGNORECASE),
    re.compile(r'("?(?:access_token|refresh_token|client_secret|token|authorization)"?\s*[:=]\s*)"?([^"\s,}]+)"?', re.IGNORECASE),
]


def redact_secrets(text: str) -> str:
    """Redact OAuth tokens, client secrets, and bearer credentials from log text."""
    redacted = text
    for pattern in _SECRET_PATTERNS:
        redacted = pattern.sub(r"\1[REDACTED]", redacted)
    return redacted


class SecretRedactingFilter(logging.Filter):
    """Logging filter that scrubs sensitive token patterns from log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = redact_secrets(record.msg)
        if record.args:
            if isinstance(record.args, tuple):
                record.args = tuple(
                    redact_secrets(a) if isinstance(a, str) else a for a in record.args
                )
            elif isinstance(record.args, dict):
                record.args = {
                    k: redact_secrets(v) if isinstance(v, str) else v
                    for k, v in record.args.items()
                }
        return True


class JsonLineFormatter(logging.Formatter):
    """Formats log records as single-line JSON for persistent audit logs."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": redact_secrets(record.getMessage()),
        }
        if record.exc_info:
            payload["exception"] = redact_secrets(self.formatException(record.exc_info))
        return json.dumps(payload, ensure_ascii=False)


class HumanConsoleFormatter(logging.Formatter):
    """Clean console format like: [INFO] Upload started."""

    def format(self, record: logging.LogRecord) -> str:
        return f"[{record.levelname}] {redact_secrets(record.getMessage())}"


def setup_logging(
    logs_dir: Path | None = None,
    *,
    json_mode: bool = False,
    level_name: str | None = None,
) -> logging.Logger:
    """Configure application logging.

    In json_mode, all console logs go to stderr so stdout remains strictly a
    single machine-readable JSON document.
    """
    resolved_level = (
        level_name or os.environ.get("MANHWA_PUBLISHER_LOG_LEVEL", "INFO")
    ).upper()
    level = getattr(logging, resolved_level, logging.INFO)

    logger = logging.getLogger("publisher")
    logger.setLevel(level)
    logger.propagate = False

    # Clear existing handlers to avoid duplicate output across repeated calls/tests.
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        handler.close()

    redactor = SecretRedactingFilter()

    console_stream = sys.stderr if json_mode else sys.stdout
    console_handler = logging.StreamHandler(console_stream)
    console_handler.setLevel(level)
    console_handler.setFormatter(HumanConsoleFormatter())
    console_handler.addFilter(redactor)
    logger.addHandler(console_handler)

    if logs_dir is not None:
        logs_dir.mkdir(parents=True, exist_ok=True)
        log_file = logs_dir / "publisher.jsonl"
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(JsonLineFormatter())
        file_handler.addFilter(redactor)
        logger.addHandler(file_handler)

    return logger
