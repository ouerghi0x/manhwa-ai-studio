"""Logging setup: application log plus per-recording log files."""
from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"


def setup_logging(log_dir: Path, level: int = logging.INFO) -> None:
    log_dir.mkdir(parents=True, exist_ok=True)
    root = logging.getLogger()
    root.setLevel(level)
    if any(getattr(h, "_manhwa_app", False) for h in root.handlers):
        return
    fh = RotatingFileHandler(log_dir / "manhwa_recorder.log", maxBytes=2_000_000,
                             backupCount=3, encoding="utf-8")
    fh.setFormatter(logging.Formatter(FORMAT))
    fh._manhwa_app = True  # type: ignore[attr-defined]
    sh = logging.StreamHandler()
    sh.setFormatter(logging.Formatter(FORMAT))
    sh._manhwa_app = True  # type: ignore[attr-defined]
    root.addHandler(fh)
    root.addHandler(sh)


class RecordingLog:
    """Context helper that mirrors all log output into a recording.log file."""

    def __init__(self, path: Path):
        self.path = path
        self.handler: logging.Handler | None = None

    def open(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.handler = logging.FileHandler(self.path, encoding="utf-8")
        self.handler.setFormatter(logging.Formatter(FORMAT))
        logging.getLogger().addHandler(self.handler)

    def close(self) -> None:
        if self.handler:
            logging.getLogger().removeHandler(self.handler)
            self.handler.close()
            self.handler = None
