"""HTTP error classification and exponential backoff retry engine."""

from __future__ import annotations

import logging
import random
import socket
import time
from collections.abc import Callable
from enum import Enum
from typing import TypeVar

import httplib2
from googleapiclient.errors import HttpError

logger = logging.getLogger("publisher.retry")

T = TypeVar("T")

RETRYABLE_HTTP_STATUSES = frozenset({408, 429, 500, 502, 503, 504})
AUTH_HTTP_STATUSES = frozenset({401})
RETRYABLE_NETWORK_EXCEPTIONS = (
    httplib2.HttpLib2Error,
    IOError,
    OSError,
    ConnectionError,
    TimeoutError,
    socket.timeout,
)


class ErrorCategory(str, Enum):
    """Classification of API/network errors for safe retry decisions."""

    RETRYABLE = "retryable"
    AUTH = "auth"
    QUOTA_EXCEEDED = "quota_exceeded"
    NON_RETRYABLE = "non_retryable"
    UNCERTAIN_TIMEOUT = "uncertain_timeout"


def classify_exception(exc: BaseException) -> ErrorCategory:
    """Classify an exception to decide whether retrying is safe."""
    if isinstance(exc, HttpError):
        status = getattr(exc.resp, "status", None)
        content_lower = ""
        try:
            content_lower = exc.content.decode("utf-8", errors="ignore").lower()
        except Exception:
            content_lower = str(exc).lower()

        if status in AUTH_HTTP_STATUSES:
            return ErrorCategory.AUTH
        if status == 403 and ("quotaexceeded" in content_lower or "dailylimitexceeded" in content_lower):
            return ErrorCategory.QUOTA_EXCEEDED
        if status in RETRYABLE_HTTP_STATUSES:
            return ErrorCategory.RETRYABLE
        return ErrorCategory.NON_RETRYABLE

    if isinstance(exc, (TimeoutError, socket.timeout)):
        return ErrorCategory.UNCERTAIN_TIMEOUT

    if isinstance(exc, RETRYABLE_NETWORK_EXCEPTIONS):
        return ErrorCategory.RETRYABLE

    return ErrorCategory.NON_RETRYABLE


def compute_backoff_seconds(
    attempt: int,
    *,
    base_delay: float = 1.0,
    max_delay: float = 64.0,
    jitter: bool = True,
) -> float:
    """Compute exponential backoff delay in seconds."""
    delay = min(max_delay, base_delay * (2 ** max(0, attempt - 1)))
    if jitter:
        delay = delay * (0.5 + random.random() * 0.5)
    return float(delay)


def execute_with_retry(
    func: Callable[[], T],
    *,
    operation_name: str,
    max_retries: int = 5,
    base_delay: float = 1.0,
    max_delay: float = 64.0,
    allow_timeout_retry: bool = True,
    sleep_fn: Callable[[float], None] = time.sleep,
) -> T:
    """Execute a callable with exponential backoff on retryable errors.

    When allow_timeout_retry is False, uncertain network timeouts are NOT blindly
    retried (critical for non-idempotent operations).
    """
    attempt = 0
    while True:
        try:
            return func()
        except Exception as exc:
            category = classify_exception(exc)
            should_retry = category == ErrorCategory.RETRYABLE or (
                category == ErrorCategory.UNCERTAIN_TIMEOUT and allow_timeout_retry
            )
            if not should_retry or attempt >= max_retries:
                raise
            attempt += 1
            delay = compute_backoff_seconds(
                attempt, base_delay=base_delay, max_delay=max_delay
            )
            logger.warning(
                "%s failed (%s). Retrying attempt %d/%d in %.2fs...",
                operation_name,
                category.value,
                attempt,
                max_retries,
                delay,
            )
            sleep_fn(delay)
