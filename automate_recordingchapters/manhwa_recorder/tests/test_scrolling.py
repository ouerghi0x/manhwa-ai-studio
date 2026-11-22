import threading
import time

from manhwa_recorder.core.scrolling_engine import (ScrollConfig, ScrollingEngine, ScrollState,
                                                   at_bottom, progress_of)


class FakePage:
    """Simulates a page: each key press scrolls by `step` px, height may grow once."""

    def __init__(self, height=5000, vh=1000, step=900, grow_at=None, grow_by=0):
        self.y, self.h, self.vh, self.step = 0, height, vh, step
        self.grow_at, self.grow_by = grow_at, grow_by
        self.keys = []
        self.lock = threading.Lock()

    def press(self, key):
        with self.lock:
            self.keys.append(key)
            self.y = min(self.h - self.vh, self.y + self.step)
            if self.grow_at is not None and self.y + self.vh >= self.grow_at:
                self.h += self.grow_by
                self.grow_at = None

    def state(self):
        with self.lock:
            return {"y": self.y, "vh": self.vh, "h": self.h}


def fast_cfg(**kw):
    base = dict(delay=0.01, initial_delay=0.0, end_hold=0.0, end_confirmations=2, max_scrolls=500)
    base.update(kw)
    return ScrollConfig(**base)


def run(engine, timeout=5):
    done = threading.Event()
    engine.on_finished = lambda r: done.set()
    engine.start()
    assert done.wait(timeout), "engine did not finish"
    engine.join(2)


def test_helpers():
    assert at_bottom({"y": 4000, "vh": 1000, "h": 5000})
    assert not at_bottom({"y": 3000, "vh": 1000, "h": 5000})
    assert progress_of({"y": 1500, "vh": 1000, "h": 5000}) == 0.5


def test_end_detection_stops_at_bottom():
    page = FakePage()
    eng = ScrollingEngine(fast_cfg(), page.press, page.state)
    run(eng)
    assert eng.state == ScrollState.FINISHED
    assert "end of chapter" in eng.finish_reason
    assert page.y + page.vh == page.h
    # 5 presses to reach bottom (4000/900 -> 5) + 1 confirmation press
    assert 5 <= eng.count <= 7
    assert all(k == "PageDown" for k in page.keys)


def test_dynamic_content_extends_scrolling():
    page = FakePage(height=4000, grow_at=3500, grow_by=3000)
    eng = ScrollingEngine(fast_cfg(), page.press, page.state)
    run(eng)
    assert page.h == 7000
    assert page.y + page.vh == 7000
    assert eng.finish_reason == "end of chapter detected"


def test_max_scrolls_limit_without_detection():
    page = FakePage(height=10**9)
    eng = ScrollingEngine(fast_cfg(end_detection=False, max_scrolls=7), page.press, None)
    run(eng)
    assert eng.count == 7
    assert eng.finish_reason == "maximum scroll actions reached"


def test_stop_interrupts_initial_delay():
    page = FakePage()
    eng = ScrollingEngine(fast_cfg(initial_delay=30), page.press, page.state)
    eng.start()
    time.sleep(0.1)
    t = time.monotonic()
    eng.stop()
    eng.join(2)
    assert time.monotonic() - t < 1
    assert eng.count == 0
    assert eng.state == ScrollState.STOPPED


def test_pause_blocks_key_presses():
    page = FakePage(height=10**9)
    eng = ScrollingEngine(fast_cfg(end_detection=False, delay=0.02, max_scrolls=10**6), page.press, None)
    eng.start()
    time.sleep(0.15)
    eng.pause()
    n = len(page.keys)
    assert eng.state == ScrollState.PAUSED
    time.sleep(0.25)
    assert len(page.keys) == n, "keys were sent while paused"
    eng.resume()
    time.sleep(0.15)
    assert len(page.keys) > n
    eng.stop()
    eng.join(2)


def test_configured_key_and_delay_respected():
    page = FakePage(height=10**9)
    eng = ScrollingEngine(fast_cfg(key="ArrowDown", delay=0.1, end_detection=False, max_scrolls=4),
                          page.press, None)
    t = time.monotonic()
    run(eng)
    assert page.keys == ["ArrowDown"] * 4
    assert time.monotonic() - t >= 0.35


def test_stall_detection():
    class Stuck(FakePage):
        def press(self, key):
            self.keys.append(key)  # page never moves and is not at bottom
    page = Stuck()
    eng = ScrollingEngine(fast_cfg(stall_limit=4), page.press, page.state)
    run(eng)
    assert "stalled" in eng.finish_reason
    assert eng.count == 4
