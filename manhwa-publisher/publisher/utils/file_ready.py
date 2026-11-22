"""File readiness checker for files being written by another AI agent."""

from __future__ import annotations

import time
from pathlib import Path


def wait_for_file_ready(
    file_path: Path,
    *,
    timeout_seconds: float = 60.0,
    poll_seconds: float = 0.5,
    stable_checks: int = 2,
) -> Path:
    """Wait until a file exists, is non-empty, is readable, and its size stabilizes.

    Raises FileNotFoundError if the file never appears within timeout_seconds,
    or TimeoutError if it remains locked or keeps growing past timeout_seconds.
    """
    deadline = time.monotonic() + max(0.0, timeout_seconds)
    last_size: int | None = None
    consecutive_stable = 0

    while True:
        if file_path.exists() and file_path.is_file():
            try:
                size = file_path.stat().st_size
                if size > 0:
                    with file_path.open("rb"):
                        pass
                    if last_size == size:
                        consecutive_stable += 1
                    else:
                        last_size = size
                        consecutive_stable = 1
                    if consecutive_stable >= stable_checks or timeout_seconds <= 0:
                        return file_path
            except OSError:
                consecutive_stable = 0

        if time.monotonic() >= deadline:
            if not file_path.exists():
                raise FileNotFoundError(f"File not found after waiting: {file_path}")
            if file_path.stat().st_size == 0:
                raise TimeoutError(f"File remained empty after waiting: {file_path}")
            return file_path

        time.sleep(min(poll_seconds, max(0.01, deadline - time.monotonic())))
