"""Filename sanitising and collision-free path helpers."""
from __future__ import annotations

import re
from pathlib import Path

_INVALID = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_RESERVED = {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)),
             *(f"LPT{i}" for i in range(1, 10))}


def sanitize_name(name: str, replacement: str = "-", max_len: int = 120) -> str:
    """Make a string safe to use as a Windows file/folder name."""
    s = _INVALID.sub(replacement, name.strip())
    s = re.sub(r"\s+", replacement, s)
    s = re.sub(rf"{re.escape(replacement)}+", replacement, s)
    s = s.strip(" .-_")
    if not s:
        s = "untitled"
    if s.upper() in _RESERVED:
        s = f"_{s}"
    return s[:max_len].rstrip(" .")


def unique_path(path: Path) -> Path:
    """Return path, or path with -take2, -take3... appended if it already exists."""
    if not path.exists():
        return path
    stem, suffix = path.stem, path.suffix
    i = 2
    while True:
        candidate = path.with_name(f"{stem}-take{i}{suffix}")
        if not candidate.exists():
            return candidate
        i += 1


def human_size(num_bytes: int) -> str:
    size = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size:.1f} {unit}" if unit != "B" else f"{int(size)} B"
        size /= 1024
    return f"{size:.1f} GB"


def check_writable_dir(path: Path) -> None:
    """Create the directory if needed and verify it is writable; raise OSError otherwise."""
    path.mkdir(parents=True, exist_ok=True)
    probe = path / ".write_test"
    probe.write_text("ok", encoding="utf-8")
    probe.unlink()
