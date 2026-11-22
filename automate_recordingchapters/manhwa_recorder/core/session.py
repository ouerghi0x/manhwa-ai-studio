"""RecordingSession: orchestrates browser + FFmpeg + scrolling for one chapter.

Contains no GUI code; it reports through callbacks (called from worker threads).
"""
from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

from ..config.settings import AppSettings
from ..utils import ffmpeg as ff
from ..utils.file_manager import check_writable_dir
from ..utils.logger import RecordingLog
from ..utils.validators import validate_url
from .browser_controller import BrowserController
from .chapter_manager import ChapterManager, ChapterPaths
from .metadata_manager import MetadataManager, RecordingMetadata
from .recording_engine import RecordingEngine, RecState
from .scrolling_engine import ScrollConfig, ScrollingEngine

log = logging.getLogger(__name__)


@dataclass
class SessionCallbacks:
    on_state: Callable[[str], None] = lambda s: None
    on_scroll: Callable[[int, Optional[float]], None] = lambda c, p: None
    on_done: Callable[[dict], None] = lambda r: None  # {"ok", "video", "error", "reason"}


@dataclass
class SessionResult:
    ok: bool
    video: str = ""
    error: str = ""
    reason: str = ""
    duration: float = 0.0
    scrolls: int = 0
    extra: dict = field(default_factory=dict)


class RecordingSession:
    _global_lock = threading.Lock()  # prevents simultaneous recordings app-wide

    def __init__(self, settings: AppSettings, browser: BrowserController,
                 callbacks: SessionCallbacks, chapter: Optional[int] = None, url: Optional[str] = None):
        self.s = settings
        self.browser = browser
        self.cb = callbacks
        self.chapter = settings.project.chapter_number if chapter is None else chapter
        self.url = url or settings.project.resolved_url()
        self.paths: Optional[ChapterPaths] = None
        self.recorder: Optional[RecordingEngine] = None
        self.scroller: Optional[ScrollingEngine] = None
        self.state = "idle"
        self._rec_log: Optional[RecordingLog] = None
        self._finish_once = threading.Lock()
        self._finished = False
        self._owns_global = False
        self.input_args_override: Optional[list[str]] = None  # test hook (replaces screen capture)
        self._tab_video_dir: Optional[Path] = None
        self._tab_start_time: float = 0.0

    # ----------------------------------------------------------------- helpers
    def _set_state(self, s: str) -> None:
        self.state = s
        self.cb.on_state(s)

    def _capture_region(self) -> Optional[ff.Region]:
        r = self.s.recording
        if r.capture_mode == "desktop":
            return None
        if r.capture_mode == "region":
            return ff.Region(r.region_x, r.region_y, r.region_w, r.region_h)

        reg = self.browser.content_region()
        # If crop_mode is auto_comic, narrow down the capture region directly to the comic column
        if r.crop_mode == "auto_comic":
            box = self.browser.get_comic_content_box()
            if box and box.get("w", 0) > 100:
                # box is in client viewport coordinates (x relative to browser viewport)
                # Map client x to screen x
                screen_x = reg.x + int(box["x"])
                screen_w = int(box["w"])
                return ff.Region(screen_x + r.browser_offset_x, reg.y + r.browser_offset_y,
                                 screen_w + r.browser_offset_w, reg.h + r.browser_offset_h)
        elif r.crop_mode == "custom" and r.crop_w > 16:
            screen_x = reg.x + r.crop_x
            screen_y = reg.y + r.crop_y
            return ff.Region(screen_x + r.browser_offset_x, screen_y + r.browser_offset_y,
                             r.crop_w + r.browser_offset_w, r.crop_h + r.browser_offset_h)

        return ff.Region(reg.x + r.browser_offset_x, reg.y + r.browser_offset_y,
                         reg.w + r.browser_offset_w, reg.h + r.browser_offset_h)

    # ----------------------------------------------------------------- control
    def start(self) -> None:
        if not RecordingSession._global_lock.acquire(blocking=False):
            raise RuntimeError("Another recording is already running")
        self._owns_global = True
        try:
            self._start()
        except Exception:
            self._release()
            raise

    def _start(self) -> None:
        err = validate_url(self.url)
        if err:
            raise ValueError(err)
        rs = self.s.recording
        if rs.engine_mode != "playwright_tab" and not self.browser.is_alive():
            raise RuntimeError("Browser is not running. Launch it and open the chapter first.")
        ffmpeg_path = ff.find_ffmpeg(rs.ffmpeg_path)
        out_root = Path(self.s.project.output_dir)
        check_writable_dir(out_root)
        cm = ChapterManager(out_root)
        self.paths = cm.prepare(cm.plan(self.s.project.series_name, self.chapter,
                                        self.s.project.filename, rs.container))
        self._rec_log = RecordingLog(self.paths.log)
        self._rec_log.open()
        log.info("=== Recording %s chapter %s from %s -> %s (engine: %s)",
                 self.s.project.series_name, self.chapter, self.url, self.paths.video, rs.engine_mode)

        if rs.engine_mode == "playwright_tab":
            self._tab_video_dir = self.paths.folder / f".tab_rec_{self.chapter}"
            # Start direct tab recording at the configured dimensions
            self.browser.start_tab_recording(self._tab_video_dir, width=rs.width, height=rs.height, url=self.url)
            if rs.hide_clutter:
                self.browser.hide_clutter()
            # Capture comic panel bounding box while tab is active and loaded
            self._cached_content_box = self.browser.get_comic_content_box()
            log.info("Cached comic content box: %s", self._cached_content_box)
            self._tab_start_time = time.monotonic()
        else:
            self.browser.bring_to_front()
            if rs.hide_clutter:
                self.browser.hide_clutter()
            region = self._capture_region()
            log.info("Capture region: %s", region or "full desktop")

            self.recorder = RecordingEngine(ffmpeg_path, fps=rs.fps, width=rs.width, height=rs.height,
                                            crf=rs.crf, preset=rs.preset, draw_mouse=rs.draw_mouse,
                                            on_error=self._on_ffmpeg_error)
            self.recorder.input_args = self.input_args_override
            self._set_state("starting ffmpeg")
            self.recorder.start(self.paths.folder, self.paths.base_name, region)

        sc = self.s.scroll
        cfg = ScrollConfig(key=sc.key, delay=sc.effective_delay(), initial_delay=sc.initial_delay,
                           max_scrolls=sc.max_scrolls, end_detection=sc.end_detection,
                           end_confirmations=sc.end_confirmations, stall_limit=sc.stall_limit,
                           end_hold=sc.end_hold)
        backend = sc.key_backend
        self.scroller = ScrollingEngine(
            cfg, send_key=lambda k: self.browser.press_key(k, backend),
            get_state=self.browser.scroll_state if sc.end_detection else None,
            check_end_boundary=self.browser.check_end_boundary if sc.end_detection else None,
            on_progress=self.cb.on_scroll, on_finished=self._on_scroll_finished)

        self._set_state("recording")
        self.scroller.start()

    def pause(self) -> None:
        if self.state != "recording" or not self.scroller:
            return
        self.scroller.pause()
        if self.recorder:
            self.recorder.pause()
        self._set_state("paused")

    def resume(self) -> None:
        if self.state != "paused" or not self.scroller:
            return
        if self.s.recording.engine_mode == "screen_capture":
            self.browser.bring_to_front()
        if self.recorder:
            self.recorder.resume()
        self.scroller.resume()
        self._set_state("recording")

    def stop(self, reason: str = "stopped by user") -> None:
        """Graceful stop; finalizes asynchronously."""
        threading.Thread(target=self._finish, args=(reason, False), daemon=True).start()

    def emergency_stop(self) -> None:
        threading.Thread(target=self._finish, args=("emergency stop", True), daemon=True).start()

    # ---------------------------------------------------------------- events
    def _on_scroll_finished(self, reason: str) -> None:
        if reason != "stopped by user":
            threading.Thread(target=self._finish, args=(reason, False), daemon=True).start()

    def _on_ffmpeg_error(self, msg: str) -> None:
        threading.Thread(target=self._finish, args=(f"ffmpeg error: {msg}", False), daemon=True).start()

    # -------------------------------------------------------------- finalize
    def _finish(self, reason: str, emergency: bool) -> None:
        with self._finish_once:
            if self._finished:
                return
            self._finished = True
        result = SessionResult(ok=False, reason=reason)
        try:
            if self.scroller:
                self.scroller.stop()
                if threading.current_thread().name != "scrolling":
                    self.scroller.join(10)
                result.scrolls = self.scroller.count
            if not self.paths:
                raise RuntimeError("Recording never started")
            self._set_state("finalizing")

            rs, sc = self.s.recording, self.s.scroll
            video_out: Path = self.paths.video

            if rs.engine_mode == "playwright_tab":
                raw_video_path = self.browser.stop_tab_recording()
                if not raw_video_path or not Path(raw_video_path).exists():
                    raise RuntimeError("No browser tab video was produced")
                
                # Transcode and crop via FFmpeg
                raw_path = Path(raw_video_path)
                ffmpeg_bin = ff.find_ffmpeg(rs.ffmpeg_path)

                # Check crop
                crop_filter = []
                if rs.crop_mode == "auto_comic":
                    box = getattr(self, "_cached_content_box", None) or self.browser.get_comic_content_box()
                    if box and box.get("w", 0) > 100:
                        # comic width and x inside viewport
                        cw = min(rs.width, int(box["w"]))
                        cx = max(0, min(rs.width - cw, int(box["x"])))
                        # ensure even dimensions for h264
                        cw -= cw % 2
                        cx -= cx % 2
                        crop_filter.append(f"crop={cw}:{rs.height}:{cx}:0")
                elif rs.crop_mode == "custom" and rs.crop_w > 16:
                    cw = min(rs.width, rs.crop_w) - (rs.crop_w % 2)
                    ch = min(rs.height, rs.crop_h) - (rs.crop_h % 2)
                    crop_filter.append(f"crop={cw}:{ch}:{rs.crop_x}:{rs.crop_y}")

                vf = ",".join(crop_filter + ["format=yuv420p"]) if crop_filter else "format=yuv420p"
                cmd = [
                    ffmpeg_bin, "-hide_banner", "-y", "-i", str(raw_path),
                    "-vf", vf, "-c:v", "libx264", "-crf", str(rs.crf),
                    "-preset", rs.preset, "-r", str(rs.fps), str(video_out)
                ]
                log.info("Transcoding tab video: %s", " ".join(cmd))
                import subprocess
                subprocess.run(cmd, check=True, creationflags=ff.CREATE_NO_WINDOW)

                # Clean up raw webm and temp dir
                try:
                    raw_path.unlink(missing_ok=True)
                    if self._tab_video_dir and self._tab_video_dir.exists():
                        import shutil
                        shutil.rmtree(self._tab_video_dir, ignore_errors=True)
                except Exception:
                    pass

                result.duration = time.monotonic() - self._tab_start_time
            else:
                if not self.recorder:
                    raise RuntimeError("Recorder process is missing")
                try:
                    video = self.recorder.stop(self.paths.video, timeout=3 if emergency else 15)
                except Exception:
                    if emergency:
                        self.recorder.abort()
                    raise
                result.duration = self.recorder.elapsed
                video_out = video

            size = video_out.stat().st_size
            measured = ff.probe_duration(ff.find_ffmpeg(rs.ffmpeg_path), video_out)
            if measured:
                result.duration = measured
            rs, sc = self.s.recording, self.s.scroll
            MetadataManager.write(RecordingMetadata(
                series_name=self.s.project.series_name, chapter_number=self.chapter,
                source_url=self.url, output_filename=video_out.name,
                resolution=f"{rs.width}x{rs.height}", fps=rs.fps,
                duration_seconds=round(result.duration, 2), scroll_count=result.scrolls,
                encoding={"codec": "libx264", "crf": rs.crf, "preset": rs.preset,
                          "pix_fmt": "yuv420p", "container": rs.container,
                          "engine_mode": rs.engine_mode,
                          "crop_mode": rs.crop_mode},
                scroll_settings={"key": sc.key, "delay": sc.effective_delay(),
                                 "initial_delay": sc.initial_delay, "profile": sc.profile},
                end_reason=reason, file_size_bytes=size), self.paths.metadata)
            result.ok, result.video = True, str(video_out)
            log.info("=== Finished: %s (%.1fs, %d scrolls, reason: %s)", video_out, result.duration,
                     result.scrolls, reason)
            self._set_state("done")
        except Exception as exc:
            log.exception("Finalize failed")
            result.error = str(exc)
            self._set_state("error")
        finally:
            if self._rec_log:
                self._rec_log.close()
            self._release()
            self.cb.on_done(result.__dict__)

    def _release(self) -> None:
        if self._owns_global:
            self._owns_global = False
            RecordingSession._global_lock.release()

    # ---------------------------------------------------------------- status
    @property
    def elapsed(self) -> float:
        if self.s.recording.engine_mode == "playwright_tab":
            return (time.monotonic() - self._tab_start_time) if self.state == "recording" else 0.0
        return self.recorder.elapsed if self.recorder else 0.0

    @property
    def size_bytes(self) -> int:
        if self.s.recording.engine_mode == "playwright_tab":
            if self._tab_video_dir and self._tab_video_dir.exists():
                return sum(f.stat().st_size for f in self._tab_video_dir.glob("*") if f.is_file())
            return 0
        return self.recorder.size_bytes if self.recorder else 0

    @property
    def ffmpeg_status(self) -> str:
        if self.s.recording.engine_mode == "playwright_tab":
            return f"browser tab recording ({self.state})"
        return self.recorder.ffmpeg_status if self.recorder else "idle"

    @property
    def is_active(self) -> bool:
        return self.state in ("starting ffmpeg", "recording", "paused", "finalizing")
