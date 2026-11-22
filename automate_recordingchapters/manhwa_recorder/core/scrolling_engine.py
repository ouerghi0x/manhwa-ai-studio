"""Automatic scrolling engine.

Independent of Playwright / FFmpeg: it receives a `send_key` callable and an
optional `get_state` callable returning {"y", "vh", "h"} (scroll position,
viewport height and total page height) for end-of-chapter detection.
"""
from __future__ import annotations

import logging
import threading
from dataclasses import dataclass
from enum import Enum
from typing import Callable, Optional

log = logging.getLogger(__name__)


class ScrollState(str, Enum):
    IDLE = "idle"
    WAITING = "initial delay"
    SCROLLING = "scrolling"
    PAUSED = "paused"
    FINISHED = "finished"
    STOPPED = "stopped"
    ERROR = "error"


@dataclass
class ScrollConfig:
    key: str = "PageDown"
    delay: float = 2.5
    initial_delay: float = 5.0
    max_scrolls: int = 2000
    end_detection: bool = True
    end_confirmations: int = 3
    stall_limit: int = 15
    end_hold: float = 3.0
    bottom_tolerance: int = 4


def at_bottom(state: dict, tolerance: int = 4) -> bool:
    return state["y"] + state["vh"] >= state["h"] - tolerance


def progress_of(state: dict) -> float:
    h = max(1.0, float(state["h"]))
    return max(0.0, min(1.0, (state["y"] + state["vh"]) / h))


class ScrollingEngine:
    def __init__(self, config: ScrollConfig, send_key: Callable[[str], None],
                 get_state: Optional[Callable[[], dict]] = None,
                 check_end_boundary: Optional[Callable[[], bool]] = None,
                 on_progress: Optional[Callable[[int, Optional[float]], None]] = None,
                 on_finished: Optional[Callable[[str], None]] = None):
        self.cfg = config
        self.send_key = send_key
        self.get_state = get_state
        self.check_end_boundary = check_end_boundary
        self.on_progress = on_progress
        self.on_finished = on_finished
        self.state = ScrollState.IDLE
        self.count = 0
        self.progress: Optional[float] = None
        self.finish_reason = ""
        self._stop = threading.Event()
        self._running = threading.Event()  # set = not paused
        self._running.set()
        self._action_lock = threading.Lock()
        self._thread: Optional[threading.Thread] = None

    # ----------------------------------------------------------------- control
    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            raise RuntimeError("Scrolling already running")
        self._stop.clear()
        self._running.set()
        self.count = 0
        self.progress = None
        self.finish_reason = ""
        self._thread = threading.Thread(target=self._run, name="scrolling", daemon=True)
        self._thread.start()

    def pause(self) -> None:
        """Pause; returns only after any in-flight key press has completed."""
        self._running.clear()
        with self._action_lock:
            pass
        if self.state in (ScrollState.SCROLLING, ScrollState.WAITING):
            self._prev_state = self.state
            self.state = ScrollState.PAUSED

    def resume(self) -> None:
        if self.state == ScrollState.PAUSED:
            self.state = getattr(self, "_prev_state", ScrollState.SCROLLING)
        self._running.set()

    def stop(self) -> None:
        self._stop.set()
        self._running.set()

    def join(self, timeout: Optional[float] = None) -> None:
        if self._thread:
            self._thread.join(timeout)

    @property
    def is_running(self) -> bool:
        return bool(self._thread and self._thread.is_alive())

    # -------------------------------------------------------------- internals
    def _sleep(self, seconds: float) -> bool:
        """Pause-aware interruptible sleep. Returns False if stopped."""
        remaining = seconds
        step = 0.05
        while remaining > 0:
            if self._stop.is_set():
                return False
            if not self._running.is_set():
                self._running.wait()
                continue
            t = min(step, remaining)
            if self._stop.wait(t):
                return False
            remaining -= t
        return not self._stop.is_set()

    def _finish(self, reason: str, state: ScrollState) -> None:
        self.finish_reason = reason
        self.state = state
        log.info("Scrolling ended: %s (%d scroll actions)", reason, self.count)
        if self.on_finished:
            self.on_finished(reason)

    def _read_state(self) -> Optional[dict]:
        if not self.get_state:
            return None
        try:
            return self.get_state()
        except Exception as exc:
            log.warning("Could not read scroll state: %s", exc)
            return None

    def _run(self) -> None:
        cfg = self.cfg
        try:
            self.state = ScrollState.WAITING
            if not self._sleep(cfg.initial_delay):
                return self._finish("stopped by user", ScrollState.STOPPED)
            self.state = ScrollState.SCROLLING
            end_hits = 0
            stalls = 0
            last = self._read_state()
            while True:
                if self._stop.is_set():
                    return self._finish("stopped by user", ScrollState.STOPPED)
                if not self._running.is_set():
                    self._running.wait()
                    continue
                with self._action_lock:
                    if not self._running.is_set() or self._stop.is_set():
                        continue
                    self.send_key(cfg.key)
                    self.count += 1
                if not self._sleep(cfg.delay):
                    return self._finish("stopped by user", ScrollState.STOPPED)
                cur = self._read_state()
                if cur is not None:
                    self.progress = progress_of(cur)
                if self.on_progress:
                    self.on_progress(self.count, self.progress)
                # Check target element boundary (e.g. Prev/Next bar reached)
                if cfg.end_detection and self.check_end_boundary:
                    try:
                        if self.check_end_boundary():
                            if self._sleep(cfg.end_hold):
                                return self._finish("chapter end boundary reached (Prev/Next)", ScrollState.FINISHED)
                            return self._finish("stopped by user", ScrollState.STOPPED)
                    except Exception as exc:
                        log.debug("Boundary check error: %s", exc)
                if cfg.end_detection and cur is not None:
                    moved = last is None or abs(cur["y"] - last["y"]) > 1 or cur["h"] != last["h"]
                    if at_bottom(cur, cfg.bottom_tolerance) and not moved:
                        end_hits += 1
                    elif at_bottom(cur, cfg.bottom_tolerance):
                        end_hits = max(end_hits, 1)  # reached bottom this step
                    else:
                        end_hits = 0
                    stalls = 0 if moved else stalls + 1
                    last = cur
                    if end_hits >= cfg.end_confirmations:
                        if self._sleep(cfg.end_hold):
                            return self._finish("end of chapter detected", ScrollState.FINISHED)
                        return self._finish("stopped by user", ScrollState.STOPPED)
                    if stalls >= cfg.stall_limit:
                        return self._finish("page stopped moving (stalled)", ScrollState.FINISHED)
                if self.count >= cfg.max_scrolls:
                    return self._finish("maximum scroll actions reached", ScrollState.FINISHED)
        except Exception as exc:
            log.exception("Scrolling failed")
            self._finish(f"error: {exc}", ScrollState.ERROR)
