"""Playwright browser controller.

Playwright's sync API is not thread-safe, so every call is marshalled onto one
dedicated browser thread. Public methods are safe to call from any thread.
"""
from __future__ import annotations

import concurrent.futures as cf
import logging
import queue
import threading
import time
from pathlib import Path
from typing import Any, Callable, Optional

from .site_adapters import SiteAdapter, get_adapter
from ..utils.ffmpeg import Region

log = logging.getLogger(__name__)

PW_KEYS = {"PageDown": "PageDown", "ArrowDown": "ArrowDown", "Space": "Space"}
PYAUTOGUI_KEYS = {"PageDown": "pagedown", "ArrowDown": "down", "Space": "space"}

REGION_JS = """() => {
    const dpr = window.devicePixelRatio || 1;
    const bx = Math.max(0, (window.outerWidth - window.innerWidth) / 2);
    const top = Math.max(0, window.outerHeight - window.innerHeight - bx);
    return {x: Math.round((window.screenX + bx) * dpr), y: Math.round((window.screenY + top) * dpr),
            w: Math.round(window.innerWidth * dpr), h: Math.round(window.innerHeight * dpr), dpr};
}"""


class BrowserError(RuntimeError):
    pass


class BrowserController:
    def __init__(self, on_status: Optional[Callable[[str], None]] = None):
        self.on_status = on_status
        self._q: "queue.Queue[tuple[Callable, cf.Future] | None]" = queue.Queue()
        self._thread: Optional[threading.Thread] = None
        self._pw = None
        self._browser = None  # only for CDP mode
        self._context = None
        self._page = None
        self._rec_context = None
        self._rec_page = None
        self.adapter: SiteAdapter = get_adapter("")
        self.adapter_name = "auto"
        self.status = "not launched"
        self.current_url = ""

    # ------------------------------------------------------------- threading
    def _ensure_thread(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._loop, name="browser", daemon=True)
        self._thread.start()

    def _loop(self) -> None:
        while True:
            item = self._q.get()
            if item is None:
                break
            fn, fut = item
            if fut.set_running_or_notify_cancel():
                try:
                    fut.set_result(fn())
                except BaseException as exc:  # noqa: BLE001
                    fut.set_exception(exc)

    def _call(self, fn: Callable[[], Any], timeout: Optional[float] = 120) -> Any:
        self._ensure_thread()
        if threading.current_thread() is self._thread:
            return fn()
        fut: cf.Future = cf.Future()
        self._q.put((fn, fut))
        return fut.result(timeout)

    def _set_status(self, s: str) -> None:
        self.status = s
        log.info("Browser: %s", s)
        if self.on_status:
            try:
                self.on_status(s)
            except Exception:
                pass

    # --------------------------------------------------------------- launch
    def launch(self, *, channel: str = "chrome", profile_dir: str, width: int = 1280,
               height: int = 1000, x: int = 0, y: int = 0, cdp_url: str = "",
               headless: bool = False,
               record_video_dir: str = "", record_video_size: tuple[int, int] | None = None) -> None:
        def _do():
            if self._alive():
                # If we need record_video_dir but the current context does not have it, relaunch
                if not record_video_dir or getattr(self, "_video_dir", "") == record_video_dir:
                    self._page.bring_to_front()
                    return
            self._cleanup()
            from playwright.sync_api import sync_playwright
            self._set_status("launching")
            self._pw = sync_playwright().start()
            self._video_dir = record_video_dir
            launch_kwargs = {}
            if record_video_dir:
                Path(record_video_dir).mkdir(parents=True, exist_ok=True)
                launch_kwargs["record_video_dir"] = record_video_dir
                if record_video_size:
                    launch_kwargs["record_video_size"] = {"width": record_video_size[0], "height": record_video_size[1]}

            if cdp_url:
                self._browser = self._pw.chromium.connect_over_cdp(cdp_url)
                self._browser.on("disconnected", lambda *_: self._set_status("disconnected"))
                self._context = (self._browser.contexts[0] if self._browser.contexts
                                 else self._browser.new_context(no_viewport=True, **launch_kwargs))
            else:
                Path(profile_dir).mkdir(parents=True, exist_ok=True)
                try:
                    self._context = self._pw.chromium.launch_persistent_context(
                        profile_dir, channel=channel, headless=headless, no_viewport=True,
                        args=[f"--window-size={width},{height}", f"--window-position={x},{y}",
                              "--disable-session-crashed-bubble", "--hide-crash-restore-bubble"],
                        ignore_default_args=["--enable-automation"],
                        **launch_kwargs)
                except Exception as exc:
                    self._cleanup()
                    raise BrowserError(
                        f"Could not launch {channel}. Is it installed? If the profile is in use by "
                        f"another window, close it first.\n{exc}") from exc
            self._context.on("close", lambda *_: self._set_status("closed"))
            self._page = self._context.pages[0] if self._context.pages else self._context.new_page()
            self._page.on("close", lambda *_: self._set_status("page closed"))
            self._set_status("ready (no chapter)")
        self._call(_do, timeout=90)

    def _alive(self) -> bool:
        try:
            return self._page is not None and not self._page.is_closed() and \
                (self._browser is None or self._browser.is_connected())
        except Exception:
            return False

    def is_alive(self) -> bool:
        try:
            return self._call(self._alive, timeout=10)
        except Exception:
            return False

    def _need_page(self):
        # If an active tab recording is running, operations (scrolling, evaluation) target that recording page
        if self._rec_page is not None and not self._rec_page.is_closed():
            return self._rec_page
        if not self._alive():
            # Pick another open tab if the user closed ours.
            if self._context is not None:
                try:
                    pages = [p for p in self._context.pages if not p.is_closed()]
                    if pages:
                        self._page = pages[-1]
                        return self._page
                except Exception:
                    pass
            raise BrowserError("Browser is not running or was closed. Click 'Launch browser'.")
        return self._page

    def start_tab_recording(self, video_dir: Path, width: int = 1280, height: int = 720, url: str = "") -> None:
        """Start a dedicated headless tab recording session (no extra visible browser windows)."""
        def _do():
            video_dir.mkdir(parents=True, exist_ok=True)
            target_url = url or self.current_url
            if not target_url and self._page and not self._page.is_closed():
                target_url = self._page.url

            # Launch a single dedicated headless Playwright browser if none is running
            if self._pw is None:
                from playwright.sync_api import sync_playwright
                self._pw = sync_playwright().start()
            if getattr(self, "_headless_browser", None) is None or not self._headless_browser.is_connected():
                self._headless_browser = self._pw.chromium.launch(channel="chrome", headless=False)

            # Create an isolated headless context with video recording enabled
            rec_ctx = self._headless_browser.new_context(
                record_video_dir=str(video_dir),
                record_video_size={"width": width, "height": height},
                viewport={"width": width, "height": height}
            )
            # Share cookies/login from user context if one exists
            if self._context:
                try:
                    rec_ctx.add_cookies(self._context.cookies())
                except Exception as exc:
                    log.warning("Could not copy cookies to recording tab: %s", exc)

            rec_page = rec_ctx.new_page()
            self._rec_context = rec_ctx
            self._rec_page = rec_page
            self._set_status("loading chapter in background recording tab")
            rec_page.goto(target_url, wait_until="domcontentloaded", timeout=60000)
            try:
                rec_page.wait_for_load_state("load", timeout=20000)
            except Exception:
                pass
            self.adapter = get_adapter(target_url, self.adapter_name)
            self._wait_images(15)
            self._set_status("background tab recording started")
        self._call(_do, timeout=90)

    def stop_tab_recording(self) -> Optional[str]:
        """Stop background tab recording and return path of the generated video file."""
        def _do():
            if not self._rec_context or not self._rec_page:
                return None
            video_path = None
            try:
                rec_page = self._rec_page
                video_obj = rec_page.video
                rec_page.close()
                self._rec_context.close()
                if video_obj:
                    video_path = video_obj.path()
            except Exception as exc:
                log.warning("Error stopping tab recording: %s", exc)
            finally:
                self._rec_page = None
                self._rec_context = None
                self._set_status("ready")
            return video_path
        return self._call(_do, timeout=30)

    # ------------------------------------------------------------ navigation
    def open(self, url: str, adapter_name: str = "auto", image_timeout: float = 20) -> dict:
        self.adapter_name = adapter_name

        def _do():
            page = self._need_page()
            self.adapter = get_adapter(url, adapter_name)
            self._set_status(f"loading ({self.adapter.name} adapter)")
            page.goto(url, wait_until="domcontentloaded", timeout=60000)
            try:
                page.wait_for_load_state("load", timeout=30000)
            except Exception:
                log.warning("Page 'load' event timed out; continuing")
            self.current_url = page.url
            info = self._wait_images(image_timeout)
            self._set_status(f"ready - {info['loaded']}/{info['total']} images loaded")
            return info
        return self._call(_do, timeout=180)

    def reload(self, image_timeout: float = 20) -> dict:
        def _do():
            page = self._need_page()
            self._set_status("reloading")
            page.reload(wait_until="domcontentloaded", timeout=60000)
            info = self._wait_images(image_timeout)
            self._set_status(f"ready - {info['loaded']}/{info['total']} images loaded")
            return info
        return self._call(_do, timeout=180)

    def _wait_images(self, timeout: float) -> dict:
        page = self._need_page()
        deadline = time.monotonic() + timeout
        info = {"total": 0, "loaded": 0}
        while True:
            try:
                info = page.evaluate(self.adapter.images_loaded_js())
            except Exception as exc:
                log.debug("image check failed: %s", exc)
            # lazy images below the fold won't load yet; visible ones should
            if info["total"] and info["loaded"] >= info["total"]:
                break
            if time.monotonic() > deadline:
                break
            page.wait_for_timeout(500)
        return info

    def preload_lazy_images(self, step_delay: float = 0.35, max_steps: int = 400) -> dict:
        """Scroll through the whole page so lazy images load, then return to top."""
        def _do():
            page = self._need_page()
            self._set_status("preloading lazy images")
            for _ in range(max_steps):
                st = page.evaluate(self.adapter.scroll_state_js)
                if st["y"] + st["vh"] >= st["h"] - 4:
                    page.wait_for_timeout(1000)
                    st2 = page.evaluate(self.adapter.scroll_state_js)
                    if st2["h"] == st["h"]:
                        break
                page.mouse.wheel(0, int(st["vh"] * 0.9))
                page.wait_for_timeout(int(step_delay * 1000))
            info = self._wait_images(15)
            page.evaluate("() => window.scrollTo(0, 0)")
            page.wait_for_timeout(500)
            self._set_status(f"ready - {info['loaded']}/{info['total']} images loaded")
            return info
        return self._call(_do, timeout=600)

    # -------------------------------------------------------------- actions
    def bring_to_front(self) -> None:
        self._call(lambda: self._need_page().bring_to_front(), timeout=15)

    def press_key(self, key: str, backend: str = "playwright") -> None:
        if backend == "pyautogui":
            import pyautogui
            pyautogui.FAILSAFE = True
            pyautogui.press(PYAUTOGUI_KEYS[key])
            return
        self._call(lambda: self._need_page().keyboard.press(PW_KEYS[key]), timeout=15)

    def scroll_state(self) -> dict:
        return self._call(lambda: self._need_page().evaluate(self.adapter.scroll_state_js), timeout=15)

    def scroll_to_top(self) -> None:
        self._call(lambda: self._need_page().evaluate("() => window.scrollTo(0, 0)"), timeout=15)

    def content_region(self) -> Region:
        r = self._call(lambda: self._need_page().evaluate(REGION_JS), timeout=15)
        return Region(int(r["x"]), int(r["y"]), int(r["w"]), int(r["h"]))

    def hide_clutter(self) -> None:
        """Hide fixed floating headers, navbars, footer controls, bottom buttons, and comments."""
        js = """() => {
            // 1. Hide fixed & sticky elements
            const fixed = Array.from(document.querySelectorAll('*')).filter(el => {
                const s = window.getComputedStyle(el);
                return s.position === 'fixed' || s.position === 'sticky';
            });
            fixed.forEach(el => el.style.setProperty('display', 'none', 'important'));

            // 2. Hide comments and reactions
            const commentSelectors = [
                '#comments-section', '[id*="comment"]', '[class*="comment"]',
                '[class*="reaction"]', '[class*="rating"]', 'footer', 'nav', 'header'
            ];
            document.querySelectorAll(commentSelectors.join(',')).forEach(el => {
                el.style.setProperty('display', 'none', 'important');
            });

            // 3. For AsuraScans / reader pages: hide everything after the comic container (.select-none)
            const reader = document.querySelector('.select-none');
            if (reader) {
                let curr = reader.nextElementSibling;
                while (curr) {
                    curr.style.setProperty('display', 'none', 'important');
                    curr = curr.nextElementSibling;
                }
            }

            // 4. Hide any elements containing Prev / Next buttons or "What did you think"
            Array.from(document.querySelectorAll('button, a')).forEach(el => {
                const t = (el.innerText || '').trim();
                if (t === 'Prev' || t === 'Next' || t === '< Prev' || t === 'Next >') {
                    const p = el.closest('div.w-full, div.flex, div.mx-auto');
                    if (p) {
                        p.style.setProperty('display', 'none', 'important');
                    } else {
                        el.style.setProperty('display', 'none', 'important');
                    }
                }
            });

            // 5. Hide "Tap to show controls" or similar overlays
            Array.from(document.querySelectorAll('div, button, span')).forEach(el => {
                const t = (el.innerText || '').trim();
                if (t.includes('Tap to show controls') || t.includes('READ THE NOVEL')) {
                    el.style.setProperty('display', 'none', 'important');
                }
            });
        }"""
        try:
            self._call(lambda: self._need_page().evaluate(js), timeout=10)
        except Exception as exc:
            log.debug("hide_clutter error: %s", exc)

    def check_end_boundary(self) -> bool:
        """Check if bottom Prev/Next or last comic panel has been reached."""
        try:
            return bool(self._call(lambda: self._need_page().evaluate(self.adapter.end_boundary_js), timeout=10))
        except Exception:
            return False

    def get_comic_content_box(self) -> Optional[dict]:
        """Return {x, y, w, h} of the comic panel column within the webpage viewport."""
        try:
            return self._call(lambda: self._need_page().evaluate(self.adapter.content_box_js), timeout=10)
        except Exception:
            return None

    def close_current_page_and_get_video(self) -> Optional[str]:
        """Close current recorded page and create a replacement tab, returning the video path."""
        def _do():
            if not self._alive() or not self._context:
                return None
            p = self._page
            video_obj = p.video if p else None
            new_p = self._context.new_page()
            try:
                p.close()
            except Exception:
                pass
            self._page = new_p
            self._page.on("close", lambda *_: self._set_status("page closed"))
            if video_obj:
                try:
                    return video_obj.path()
                except Exception as exc:
                    log.warning("Could not get video path: %s", exc)
            return None
        return self._call(_do, timeout=30)

    # -------------------------------------------------------------- cleanup
    def _cleanup(self) -> None:
        for obj, meth in ((self._context if self._browser is None else None, "close"),
                          (self._browser, "close"), (self._pw, "stop")):
            if obj is not None:
                try:
                    getattr(obj, meth)()
                except Exception:
                    pass
        self._pw = self._browser = self._context = self._page = None

    def close(self) -> None:
        if not (self._thread and self._thread.is_alive()):
            return
        try:
            self._call(self._cleanup, timeout=20)
        except Exception:
            pass
        self._q.put(None)
        self._set_status("not launched")
