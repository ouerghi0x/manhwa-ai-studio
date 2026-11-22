"""Manhwa Recorder entry point:  python main.py   (from the manhwa_recorder folder)
or  python -m manhwa_recorder  (from its parent folder)."""
from __future__ import annotations

import logging
import sys
from pathlib import Path

if __package__ in (None, ""):
    # Allow `python main.py` and PyInstaller: make the package importable.
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    __package__ = "manhwa_recorder"

from manhwa_recorder.config.settings import PACKAGE_DIR, AppSettings  # noqa: E402
from manhwa_recorder.utils.logger import setup_logging  # noqa: E402


def main() -> int:
    setup_logging(PACKAGE_DIR / "logs")
    log = logging.getLogger("manhwa_recorder")

    def excepthook(t, v, tb):
        log.critical("Unhandled exception", exc_info=(t, v, tb))
    sys.excepthook = excepthook

    from PySide6.QtWidgets import QApplication
    from manhwa_recorder.gui.main_window import MainWindow
    from manhwa_recorder.gui.styles import STYLESHEET

    app = QApplication(sys.argv)
    app.setApplicationName("Manhwa Recorder")
    app.setStyleSheet(STYLESHEET)
    win = MainWindow(AppSettings.load())
    win.show()
    log.info("Manhwa Recorder started")
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
