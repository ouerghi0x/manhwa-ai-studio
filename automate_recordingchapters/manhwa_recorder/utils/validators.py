"""Input validation helpers used by the GUI and the session."""
from __future__ import annotations

from urllib.parse import urlparse


def validate_url(url: str) -> str | None:
    """Return an error message, or None if the URL is acceptable."""
    if not url.strip():
        return "Chapter URL is empty"
    p = urlparse(url.strip())
    if p.scheme not in ("http", "https", "file"):
        return "URL must start with http://, https:// or file://"
    if p.scheme != "file" and not p.netloc:
        return "URL has no host"
    return None


def parse_chapter_range(text: str) -> list[int]:
    """Parse '45-48, 50, 52-53' into a sorted unique list of chapter numbers."""
    result: set[int] = set()
    for part in text.replace(";", ",").split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            a, b = (int(x) for x in part.split("-", 1))
            if b < a:
                a, b = b, a
            if b - a > 5000:
                raise ValueError("Range too large")
            result.update(range(a, b + 1))
        else:
            result.add(int(part))
    return sorted(result)
