"""Windows global hotkeys (work while the browser has focus) via RegisterHotKey."""
from __future__ import annotations

import ctypes
import logging
import sys
import threading
from ctypes import wintypes
from typing import Callable

log = logging.getLogger(__name__)

MOD_ALT, MOD_CONTROL, MOD_SHIFT, MOD_NOREPEAT = 0x1, 0x2, 0x4, 0x4000
WM_HOTKEY, WM_QUIT = 0x0312, 0x0012


class GlobalHotkeys:
    """hotkeys: list of (modifiers, virtual_key, callback). Callbacks run on a worker thread."""

    def __init__(self, hotkeys: list[tuple[int, int, Callable[[], None]]]):
        self.hotkeys = hotkeys
        self._thread_id = 0
        self._thread: threading.Thread | None = None
        self.registered: list[int] = []

    def start(self) -> None:
        if sys.platform != "win32":
            return
        self._thread = threading.Thread(target=self._run, name="hotkeys", daemon=True)
        self._thread.start()

    def _run(self) -> None:
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32
        self._thread_id = kernel32.GetCurrentThreadId()
        for i, (mods, vk, _) in enumerate(self.hotkeys, start=1):
            if user32.RegisterHotKey(None, i, mods | MOD_NOREPEAT, vk):
                self.registered.append(i)
            else:
                log.warning("Could not register global hotkey #%d (in use by another app?)", i)
        msg = wintypes.MSG()
        while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
            if msg.message == WM_HOTKEY and 1 <= msg.wParam <= len(self.hotkeys):
                try:
                    self.hotkeys[msg.wParam - 1][2]()
                except Exception:
                    log.exception("Hotkey callback failed")
        for i in self.registered:
            user32.UnregisterHotKey(None, i)

    def stop(self) -> None:
        if self._thread_id:
            ctypes.windll.user32.PostThreadMessageW(self._thread_id, WM_QUIT, 0, 0)
