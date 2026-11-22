"""FFmpeg-based screen recording engine.

Pause/resume is implemented by closing the current FFmpeg segment and starting a
new one on resume; segments are losslessly concatenated on stop. This never
corrupts the video (no frozen frames, no broken timestamps).
Segments are written as MKV so a crash still leaves a playable file.
"""
from __future__ import annotations

import atexit
import logging
import re
import subprocess
import threading
import time
from enum import Enum
from pathlib import Path
from typing import Callable, Optional

from ..utils import ffmpeg as ff

log = logging.getLogger(__name__)

_LIVE_PROCS: set[subprocess.Popen] = set()
_LIVE_LOCK = threading.Lock()


def _kill_proc_tree(p: subprocess.Popen) -> None:
    try:
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(p.pid)],
                       capture_output=True, creationflags=ff.CREATE_NO_WINDOW)
    except Exception:
        try:
            p.kill()
        except OSError:
            pass


def _kill_all_on_exit() -> None:
    with _LIVE_LOCK:
        procs = list(_LIVE_PROCS)
    for p in procs:
        if p.poll() is None:
            try:
                p.stdin.write(b"q")  # type: ignore[union-attr]
                p.stdin.flush()  # type: ignore[union-attr]
                p.wait(3)
            except Exception:
                pass
            if p.poll() is None:
                _kill_proc_tree(p)


atexit.register(_kill_all_on_exit)


class RecState(str, Enum):
    IDLE = "idle"
    RECORDING = "recording"
    PAUSED = "paused"
    FINALIZING = "finalizing"
    ERROR = "error"


class RecordingError(RuntimeError):
    pass


class _Segment:
    def __init__(self, cmd: list[str], path: Path, on_exit: Callable[["_Segment"], None]):
        self.path = path
        self.cmd = cmd
        self.stderr_tail: list[str] = []
        self.first_frame = threading.Event()
        self.stopping = False
        self.frames = 0
        self._on_exit = on_exit
        log.info("FFmpeg: %s", subprocess.list2cmdline(cmd))
        self.proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL,
                                     stderr=subprocess.PIPE, creationflags=ff.CREATE_NO_WINDOW)
        with _LIVE_LOCK:
            _LIVE_PROCS.add(self.proc)
        self._reader = threading.Thread(target=self._read_stderr, daemon=True)
        self._reader.start()

    def _read_stderr(self) -> None:
        buf = b""
        stream = self.proc.stderr
        assert stream is not None
        while True:
            chunk = stream.read1(4096) if hasattr(stream, "read1") else stream.read(1)
            if not chunk:
                break
            buf += chunk
            parts = re.split(rb"[\r\n]", buf)
            buf = parts.pop()
            for raw in parts:
                line = raw.decode("utf-8", "replace").strip()
                if not line:
                    continue
                m = re.search(r"frame=\s*(\d+)", line)
                if m:
                    self.frames = int(m.group(1))
                    if self.frames > 0:
                        self.first_frame.set()
                    continue
                self.stderr_tail.append(line)
                del self.stderr_tail[:-40]
        self.proc.wait()
        with _LIVE_LOCK:
            _LIVE_PROCS.discard(self.proc)
        self._on_exit(self)

    def alive(self) -> bool:
        return self.proc.poll() is None

    def stop(self, timeout: float = 15.0) -> int:
        self.stopping = True
        if self.alive():
            try:
                self.proc.stdin.write(b"q")  # type: ignore[union-attr]
                self.proc.stdin.flush()  # type: ignore[union-attr]
                self.proc.stdin.close()  # type: ignore[union-attr]
            except OSError:
                pass
            try:
                self.proc.wait(timeout)
            except subprocess.TimeoutExpired:
                log.warning("FFmpeg did not exit gracefully; killing it")
                _kill_proc_tree(self.proc)
                self.proc.wait(5)
        self._reader.join(5)
        return self.proc.returncode


class RecordingEngine:
    def __init__(self, ffmpeg_path: str, *, fps: int = 30, width: int = 1920, height: int = 1080,
                 crf: int = 18, preset: str = "veryfast", draw_mouse: bool = False,
                 on_error: Optional[Callable[[str], None]] = None):
        self.ffmpeg = ffmpeg_path
        self.fps, self.width, self.height = fps, width, height
        self.crf, self.preset, self.draw_mouse = crf, preset, draw_mouse
        self.on_error = on_error
        self.state = RecState.IDLE
        self.region: ff.Region | None = None
        self._segments: list[Path] = []
        self._current: _Segment | None = None
        self._lock = threading.RLock()
        self._work_dir: Path | None = None
        self._base: str = ""
        self._elapsed_before = 0.0
        self._seg_started = 0.0
        self.last_error = ""
        self.input_args: list[str] | None = None  # test hook: replaces gdigrab input
    @property
    def elapsed(self) -> float:
        with self._lock:
            if self.state == RecState.RECORDING:
                return self._elapsed_before + (time.monotonic() - self._seg_started)
            return self._elapsed_before

    @property
    def size_bytes(self) -> int:
        total = 0
        for p in list(self._segments):
            try:
                total += p.stat().st_size
            except OSError:
                pass
        return total

    @property
    def ffmpeg_status(self) -> str:
        seg = self._current
        if seg and seg.alive():
            return f"running (pid {seg.proc.pid}, {seg.frames} frames)"
        if self.last_error:
            return f"error: {self.last_error}"
        return self.state.value

    # ----------------------------------------------------------------- control
    def start(self, work_dir: Path, base_name: str, region: ff.Region | None) -> None:
        with self._lock:
            if self.state not in (RecState.IDLE, RecState.ERROR):
                raise RecordingError("A recording is already in progress")
            self._work_dir, self._base, self.region = work_dir, base_name, region
            self._segments.clear()
            self._elapsed_before = 0.0
            self.last_error = ""
            work_dir.mkdir(parents=True, exist_ok=True)
            self._start_segment()
            self.state = RecState.RECORDING

    def _start_segment(self) -> None:
        assert self._work_dir is not None
        idx = len(self._segments) + 1
        path = self._work_dir / f".{self._base}.part{idx:03d}.mkv"
        cmd = ff.build_capture_command(self.ffmpeg, path, fps=self.fps, width=self.width,
                                       height=self.height, crf=self.crf, preset=self.preset,
                                       region=self.region, draw_mouse=self.draw_mouse,
                                       input_args=self.input_args)
        seg = _Segment(cmd, path, self._segment_exited)
        if not seg.first_frame.wait(15) or not seg.alive():
            seg.stop(5)
            msg = "; ".join(seg.stderr_tail[-5:]) or "FFmpeg produced no frames"
            hint = ff.explain_error(seg.stderr_tail)
            if hint:
                msg = f"{hint}\n\nFFmpeg: {msg}"
            self.last_error = msg
            self.state = RecState.ERROR
            raise RecordingError(f"FFmpeg failed to start: {msg}")
        self._segments.append(path)
        self._current = seg
        self._seg_started = time.monotonic()

    def _segment_exited(self, seg: _Segment) -> None:
        if seg.stopping or seg is not self._current:
            return  # graceful stop, or a failed start (reported by _start_segment)
        msg = f"FFmpeg exited unexpectedly (code {seg.proc.returncode}): " + \
              "; ".join(seg.stderr_tail[-3:])
        log.error(msg)
        with self._lock:
            if self._current is seg and self.state == RecState.RECORDING:
                self._elapsed_before += time.monotonic() - self._seg_started
                self.state = RecState.ERROR
                self.last_error = msg
        if self.on_error:
            self.on_error(msg)

    def pause(self) -> None:
        with self._lock:
            if self.state != RecState.RECORDING or not self._current:
                return
            self._current.stop()
            self._elapsed_before += time.monotonic() - self._seg_started
            self._current = None
            self.state = RecState.PAUSED
            log.info("Recording paused at %.1fs", self._elapsed_before)

    def resume(self) -> None:
        with self._lock:
            if self.state != RecState.PAUSED:
                return
            self._start_segment()
            self.state = RecState.RECORDING
            log.info("Recording resumed")

    def stop(self, final_path: Path, timeout: float = 15.0) -> Path:
        """Stop and finalize into final_path. Returns the written file."""
        with self._lock:
            if self.state == RecState.IDLE:
                raise RecordingError("Not recording")
            if self._current:
                was_recording = self.state == RecState.RECORDING
                self._current.stop(timeout)
                if was_recording:
                    self._elapsed_before += time.monotonic() - self._seg_started
                self._current = None
            self.state = RecState.FINALIZING
        try:
            return self._finalize(final_path)
        finally:
            with self._lock:
                self.state = RecState.IDLE

    def _finalize(self, final_path: Path) -> Path:
        segs = [p for p in self._segments if p.exists() and p.stat().st_size > 0]
        if not segs:
            raise RecordingError("No recorded data to finalize")
        assert self._work_dir is not None
        list_file = self._work_dir / f".{self._base}.concat.txt"
        list_file.write_text("".join(ff.concat_list_line(p) for p in segs), encoding="utf-8")
        cmd = ff.build_concat_command(self.ffmpeg, list_file, final_path)
        log.info("Finalizing %d segment(s) -> %s", len(segs), final_path)
        r = subprocess.run(cmd, capture_output=True, text=True, creationflags=ff.CREATE_NO_WINDOW,
                           encoding="utf-8", errors="replace")
        if r.returncode != 0 or not final_path.exists():
            raise RecordingError(f"Finalizing failed; segments kept in {self._work_dir}: "
                                 f"{r.stderr.strip()[-500:]}")
        for p in segs:
            p.unlink(missing_ok=True)
        list_file.unlink(missing_ok=True)
        self._segments.clear()
        return final_path

    def abort(self) -> None:
        """Emergency: kill FFmpeg immediately, keep whatever segments exist."""
        with self._lock:
            if self._current:
                self._current.stopping = True
                _kill_proc_tree(self._current.proc)
                self._current = None
            self.state = RecState.IDLE

    def snapshot(self, out_png: Path, region: ff.Region | None) -> Path:
        cmd = ff.build_snapshot_command(self.ffmpeg, out_png, region)
        r = subprocess.run(cmd, capture_output=True, text=True, creationflags=ff.CREATE_NO_WINDOW,
                           timeout=20)
        if r.returncode != 0:
            raise RecordingError(r.stderr.strip()[-300:])
        return out_png
