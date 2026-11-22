"""Streaming SHA-256 hashing utilities for duplicate video detection."""

from __future__ import annotations

import hashlib
from pathlib import Path

_CHUNK_SIZE = 1024 * 1024  # 1 MiB


def compute_sha256(file_path: Path) -> str:
    """Compute the lowercase hex SHA-256 digest of a file without loading it into RAM."""
    digest = hashlib.sha256()
    with file_path.open("rb") as handle:
        while True:
            chunk = handle.read(_CHUNK_SIZE)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()
