"""Main window. GUI only: all work is delegated to core/ classes on worker threads."""
from __future__ import annotations

import logging
import os
import tempfile
import time
from pathlib import Path
from typing import Any, Callable, Optional

from PySide6.QtCore import QObject, QRunnable, Qt, QThreadPool, QTimer, Signal, Slot
from PySide6.QtGui import QDesktopServices, QKeySequence, QPixmap, QShortcut
from PySide6.QtCore import QUrl
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QDoubleSpinBox, QFileDialog,
                               QFormLayout, QGridLayout, QGroupBox, QHBoxLayout, QLabel,
                               QLineEdit, QListWidget, QListWidgetItem, QMainWindow, QMessageBox,
                               QPlainTextEdit, QProgressBar, QPushButton, QScrollArea, QSpinBox,
                               QVBoxLayout, QWidget)

from ..config.settings import AppSettings
from ..core.batch_manager import BatchManager
from ..core.browser_controller import BrowserController
from ..core.recording_engine import RecordingEngine
from ..core.session import RecordingSession, SessionCallbacks
from ..utils import ffmpeg as ff
from ..utils.file_manager import human_size
from ..utils.hotkeys import MOD_ALT, MOD_CONTROL, GlobalHotkeys
from ..utils.validators import validate_url
from .chapter_dialog import ChapterDialog
from .settings_dialog import SettingsDialog

log = logging.getLogger(__name__)
RESOLUTIONS = ["1920x1080", "1280x720", "2560x1440", "3840x2160", "1080x1920"]


# ----------------------------------------------------------------- threading
class _WorkerSignals(QObject):
    ok = Signal(object)
    err = Signal(str)


class _Worker(QRunnable):
    def __init__(self, fn: Callable[[], Any]):
        super().__init__()
        self.fn = fn
        self.signals = _WorkerSignals()

    @Slot()
    def run(self) -> None:
        try:
            res = self.fn()
        except Exception as exc:  # noqa: BLE001
            log.exception("Background task failed")
            self.signals.err.emit(str(exc))
        else:
            self.signals.ok.emit(res)


class Bridge(QObject):
    """Thread -> GUI signal bridge."""
    state = Signal(str)
    scroll = Signal(int, object)
    done = Signal(dict)
    browser_status = Signal(str)
    log_line = Signal(str)
    hotkey = Signal(str)


class _QtLogHandler(logging.Handler):
    def __init__(self, bridge: Bridge):
        super().__init__()
        self.bridge = bridge
        self.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s", "%H:%M:%S"))

    def emit(self, record: logging.LogRecord) -> None:
        try:
            self.bridge.log_line.emit(self.format(record))
        except RuntimeError:
            pass


def _value_label(text: str = "-") -> QLabel:
    lbl = QLabel(text)
    lbl.setObjectName("value")
    lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)
    lbl.setWordWrap(True)
    return lbl


class MainWindow(QMainWindow):
    def __init__(self, settings: AppSettings):
        super().__init__()
        self.settings = settings
        self.pool = QThreadPool.globalInstance()
        self.bridge = Bridge()
        self.browser = BrowserController(on_status=self.bridge.browser_status.emit)
        self.session: Optional[RecordingSession] = None
        self.batch = BatchManager()
        self._workers: set[_Worker] = set()
        self._countdown = 0
        self._busy = False
        self.ffmpeg_caps: Optional[ff.FFmpegCaps] = None

        self.setWindowTitle("Manhwa Recorder")
        self.resize(1180, 860)
        self._build_ui()
        self._load_into_widgets()
        self._connect()

        handler = _QtLogHandler(self.bridge)
        handler.setLevel(logging.INFO)
        logging.getLogger().addHandler(handler)
        self._log_handler = handler

        self.timer = QTimer(self, interval=250, timeout=self._tick)
        self.timer.start()
        self.countdown_timer = QTimer(self, interval=1000, timeout=self._countdown_tick)

        self.hotkeys = GlobalHotkeys([
            (MOD_CONTROL | MOD_ALT, ord("P"), lambda: self.bridge.hotkey.emit("pause")),
            (MOD_CONTROL | MOD_ALT, ord("S"), lambda: self.bridge.hotkey.emit("stop")),
            (MOD_CONTROL | MOD_ALT, ord("E"), lambda: self.bridge.hotkey.emit("emergency")),
        ])
        self.hotkeys.start()
        QTimer.singleShot(100, self._check_environment)
        self._update_buttons()

    # ================================================================== UI
    def _build_ui(self) -> None:
        root = QWidget()
        outer = QHBoxLayout(root)
        left_w, right_w = QWidget(), QWidget()
        left, right = QVBoxLayout(left_w), QVBoxLayout(right_w)
        for l in (left, right):
            l.setContentsMargins(4, 0, 4, 0)

        # --- Project
        g = QGroupBox("Project")
        f = QFormLayout(g)
        self.series = QLineEdit()
        f.addRow("Manhwa name", self.series)
        self.chapter = QSpinBox()
        self.chapter.setRange(0, 100000)
        f.addRow("Chapter number", self.chapter)
        self.url_template = QLineEdit()
        self.url_template.setToolTip("Use {chapter} as placeholder for the chapter number")
        f.addRow("URL template", self.url_template)
        self.chapter_url = QLineEdit()
        self.chapter_url.setPlaceholderText("auto from template; type a URL to override")
        f.addRow("Chapter URL", self.chapter_url)
        self.filename = QLineEdit()
        self.filename.setPlaceholderText("auto (chapter-007)")
        f.addRow("Filename", self.filename)
        self.output_dir = QLineEdit()
        b = QPushButton("…")
        b.setFixedWidth(34)
        b.clicked.connect(self._browse_output)
        row = QHBoxLayout()
        row.addWidget(self.output_dir)
        row.addWidget(b)
        f.addRow("Output folder", row)
        left.addWidget(g)

        # --- Recording settings
        g = QGroupBox("Recording settings")
        f = QFormLayout(g)
        self.engine_mode = QComboBox()
        self.engine_mode.addItems(["playwright_tab", "screen_capture"])
        self.engine_mode.setToolTip("playwright_tab: Records only the browser tab in background (no PC screen, no interference).\nscreen_capture: Uses Windows screen capture.")
        f.addRow("Engine", self.engine_mode)
        self.resolution = QComboBox()
        self.resolution.setEditable(True)
        self.resolution.addItems(RESOLUTIONS)
        f.addRow("Resolution", self.resolution)
        self.fps = QSpinBox()
        self.fps.setRange(1, 120)
        f.addRow("FPS", self.fps)
        self.crf = QSpinBox()
        self.crf.setRange(0, 51)
        self.crf.setToolTip("CRF: lower = better quality / bigger file. 18 ≈ visually lossless.")
        f.addRow("Quality (CRF)", self.crf)
        self.container = QComboBox()
        self.container.addItems(["mp4", "mkv"])
        f.addRow("Format", self.container)
        self.scroll_key = QComboBox()
        self.scroll_key.addItems(["PageDown", "ArrowDown", "Space"])
        f.addRow("Scroll key", self.scroll_key)
        self.profile = QComboBox()
        self.profile.addItems(["Slow", "Normal", "Fast", "Custom"])
        f.addRow("Scroll profile", self.profile)
        self.delay = QDoubleSpinBox()
        self.delay.setRange(0.1, 120)
        self.delay.setSingleStep(0.25)
        self.delay.setSuffix(" s")
        f.addRow("Scroll delay", self.delay)
        self.initial_delay = QDoubleSpinBox()
        self.initial_delay.setRange(0, 600)
        self.initial_delay.setSuffix(" s")
        f.addRow("Initial delay", self.initial_delay)
        self.crop_mode = QComboBox()
        self.crop_mode.addItems(["auto_comic", "none", "custom"])
        self.crop_mode.setToolTip("auto_comic: automatically crops black side margins and centers on comic panels.")
        f.addRow("Crop to Comic", self.crop_mode)
        self.end_detect = QCheckBox("Stop automatically at Prev / Next buttons")
        f.addRow("", self.end_detect)
        self.btn_settings = QPushButton("Advanced settings…")
        f.addRow("", self.btn_settings)
        left.addWidget(g)

        # --- Batch
        g = QGroupBox("Batch recording")
        v = QVBoxLayout(g)
        self.batch_list = QListWidget()
        self.batch_list.setMinimumHeight(110)
        v.addWidget(self.batch_list)
        row = QHBoxLayout()
        self.btn_batch_add = QPushButton("Add chapters…")
        self.btn_batch_remove = QPushButton("Remove")
        self.btn_batch_clear = QPushButton("Clear")
        for w in (self.btn_batch_add, self.btn_batch_remove, self.btn_batch_clear):
            row.addWidget(w)
        v.addLayout(row)
        row = QHBoxLayout()
        self.btn_batch_start = QPushButton("Start batch")
        self.btn_batch_next = QPushButton("Record this chapter ▶")
        self.btn_batch_next.setObjectName("primary")
        self.btn_batch_cancel = QPushButton("Cancel batch")
        for w in (self.btn_batch_start, self.btn_batch_next, self.btn_batch_cancel):
            row.addWidget(w)
        v.addLayout(row)
        row = QHBoxLayout()
        self.btn_batch_package = QPushButton("📦 Package chaptersXtoY")
        self.btn_batch_package.setToolTip("Gather all batch episodes into one folder (chaptersXtoY) and generate all pipeline .md files")
        self.btn_batch_publish = QPushButton("🚀 manhwa-publisher")
        self.btn_batch_publish.setToolTip("Show commands and validate package with manhwa-publisher CLI")
        for w in (self.btn_batch_package, self.btn_batch_publish):
            row.addWidget(w)
        v.addLayout(row)
        self.batch_info = QLabel("")
        self.batch_info.setObjectName("hint")
        self.batch_info.setWordWrap(True)
        v.addWidget(self.batch_info)
        left.addWidget(g)
        left.addStretch(1)

        # --- Browser
        g = QGroupBox("Browser")
        grid = QGridLayout(g)
        self.btn_launch = QPushButton("Launch browser")
        self.btn_open = QPushButton("Open chapter")
        self.btn_reload = QPushButton("Reload chapter")
        self.btn_preload = QPushButton("Preload images")
        self.btn_preload.setToolTip("Scroll through the page once so lazy-loaded images load, then return to top")
        self.btn_test_capture = QPushButton("Test capture region")
        self.btn_test_capture.setToolTip("Grab one frame with the current capture settings and show it")
        for i, w in enumerate((self.btn_launch, self.btn_open, self.btn_reload,
                               self.btn_preload, self.btn_test_capture)):
            grid.addWidget(w, i // 3, i % 3)
        self.browser_status = _value_label("not launched")
        grid.addWidget(QLabel("Status:"), 2, 0)
        grid.addWidget(self.browser_status, 2, 1, 1, 2)
        right.addWidget(g)

        # --- Recording controls
        g = QGroupBox("Recording")
        row = QHBoxLayout(g)
        self.btn_start = QPushButton("● Start Recording")
        self.btn_start.setObjectName("primary")
        self.btn_pause = QPushButton("Pause")
        self.btn_resume = QPushButton("Resume")
        self.btn_stop = QPushButton("■ Stop")
        self.btn_emergency = QPushButton("Emergency Stop")
        self.btn_emergency.setObjectName("danger")
        for w in (self.btn_start, self.btn_pause, self.btn_resume, self.btn_stop, self.btn_emergency):
            row.addWidget(w)
        right.addWidget(g)
        hint = QLabel("Global hotkeys (work while the browser has focus): Ctrl+Alt+P pause/resume · "
                      "Ctrl+Alt+S stop · Ctrl+Alt+E emergency stop")
        hint.setObjectName("hint")
        hint.setWordWrap(True)
        right.addWidget(hint)

        # --- Live status
        g = QGroupBox("Live status")
        f = QFormLayout(g)
        self.lbl_state = QLabel("idle")
        self.lbl_state.setObjectName("rec")
        f.addRow("Recording", self.lbl_state)
        self.lbl_elapsed = _value_label("00:00")
        f.addRow("Elapsed", self.lbl_elapsed)
        self.lbl_size = _value_label("-")
        f.addRow("File size", self.lbl_size)
        self.lbl_scrolls = _value_label("0")
        f.addRow("Scroll actions", self.lbl_scrolls)
        self.lbl_path = _value_label("-")
        f.addRow("Recording path", self.lbl_path)
        self.lbl_ffmpeg = _value_label("-")
        f.addRow("FFmpeg", self.lbl_ffmpeg)
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setFormat("waiting")
        f.addRow("Progress", self.progress)
        row = QHBoxLayout()
        self.btn_open_folder = QPushButton("Open output folder")
        row.addWidget(self.btn_open_folder)
        row.addStretch(1)
        f.addRow("", row)
        right.addWidget(g)

        # --- Log
        g = QGroupBox("Log")
        v = QVBoxLayout(g)
        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setMaximumBlockCount(2000)
        v.addWidget(self.log_view)
        right.addWidget(g, 1)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(left_w)
        scroll.setMinimumWidth(470)
        outer.addWidget(scroll, 0)
        outer.addWidget(right_w, 1)
        self.setCentralWidget(root)

    def _connect(self) -> None:
        self.btn_launch.clicked.connect(self.launch_browser)
        self.btn_open.clicked.connect(lambda: self.open_chapter())
        self.btn_reload.clicked.connect(self.reload_chapter)
        self.btn_preload.clicked.connect(self.preload_images)
        self.btn_test_capture.clicked.connect(self.test_capture)
        self.btn_start.clicked.connect(lambda: self.start_recording())
        self.btn_pause.clicked.connect(self.pause)
        self.btn_resume.clicked.connect(self.resume)
        self.btn_stop.clicked.connect(self.stop)
        self.btn_emergency.clicked.connect(self.emergency_stop)
        self.btn_settings.clicked.connect(self.open_settings)
        self.btn_open_folder.clicked.connect(self.open_output_folder)
        self.btn_batch_add.clicked.connect(self.batch_add)
        self.btn_batch_remove.clicked.connect(self.batch_remove)
        self.btn_batch_clear.clicked.connect(self.batch_clear)
        self.btn_batch_start.clicked.connect(self.batch_start)
        self.btn_batch_next.clicked.connect(self.batch_record_current)
        self.btn_batch_cancel.clicked.connect(self.batch_cancel)
        self.btn_batch_package.clicked.connect(lambda: self.batch_package(auto=False))
        self.btn_batch_publish.clicked.connect(self.open_manhwa_publisher)
        self.profile.currentTextChanged.connect(self._profile_changed)
        self.chapter.valueChanged.connect(self._update_url_placeholder)
        self.url_template.textChanged.connect(self._update_url_placeholder)
        self.bridge.state.connect(self._on_state)
        self.bridge.scroll.connect(self._on_scroll)
        self.bridge.done.connect(self._on_done)
        self.bridge.browser_status.connect(self.browser_status.setText)
        self.bridge.log_line.connect(self.log_view.appendPlainText)
        self.bridge.hotkey.connect(self._on_hotkey)
        QShortcut(QKeySequence("Ctrl+Shift+X"), self, activated=self.emergency_stop)

    # ============================================================ settings
    def _load_into_widgets(self) -> None:
        s = self.settings
        p, r, sc = s.project, s.recording, s.scroll
        self.series.setText(p.series_name)
        self.chapter.setValue(p.chapter_number)
        self.url_template.setText(p.url_template)
        self.chapter_url.setText(p.chapter_url)
        self.filename.setText(p.filename)
        self.output_dir.setText(p.output_dir)
        self.engine_mode.setCurrentText(r.engine_mode)
        self.resolution.setCurrentText(f"{r.width}x{r.height}")
        self.fps.setValue(r.fps)
        self.crf.setValue(r.crf)
        self.container.setCurrentText(r.container)
        self.scroll_key.setCurrentText(sc.key)
        self.profile.setCurrentText(sc.profile)
        self.delay.setValue(sc.delay if sc.profile == "Custom" else sc.effective_delay())
        self.delay.setEnabled(sc.profile == "Custom")
        self.initial_delay.setValue(sc.initial_delay)
        self.crop_mode.setCurrentText(r.crop_mode)
        self.end_detect.setChecked(sc.end_detection)
        self._update_url_placeholder()

    def _collect(self) -> AppSettings:
        """Read widgets into a validated AppSettings (raises ValueError)."""
        data = self.settings.model_dump()
        res = self.resolution.currentText().lower().replace(" ", "")
        try:
            w, h = (int(x) for x in res.split("x"))
        except ValueError:
            raise ValueError("Resolution must look like 1920x1080")
        data["project"].update(series_name=self.series.text(), chapter_number=self.chapter.value(),
                               url_template=self.url_template.text().strip(),
                               chapter_url=self.chapter_url.text().strip(),
                               filename=self.filename.text().strip(),
                               output_dir=self.output_dir.text().strip())
        data["recording"].update(width=w, height=h, fps=self.fps.value(), crf=self.crf.value(),
                                 container=self.container.currentText(),
                                 engine_mode=self.engine_mode.currentText(),
                                 crop_mode=self.crop_mode.currentText())
        data["scroll"].update(key=self.scroll_key.currentText(), profile=self.profile.currentText(),
                              delay=self.delay.value(), initial_delay=self.initial_delay.value(),
                              end_detection=self.end_detect.isChecked())
        s = AppSettings.model_validate(data)
        self.settings = s
        return s

    def _try_collect(self) -> Optional[AppSettings]:
        try:
            return self._collect()
        except Exception as exc:
            QMessageBox.warning(self, "Invalid settings", str(exc))
            return None

    def _profile_changed(self, name: str) -> None:
        from ..config.settings import SCROLL_PROFILES
        self.delay.setEnabled(name == "Custom")
        if name in SCROLL_PROFILES:
            self.delay.setValue(SCROLL_PROFILES[name])

    def _update_url_placeholder(self) -> None:
        tpl = self.url_template.text()
        try:
            url = tpl.format(chapter=self.chapter.value()) if "{chapter}" in tpl else tpl
        except (KeyError, IndexError, ValueError):
            url = tpl
        self.chapter_url.setPlaceholderText(url or "enter chapter URL")

    def _browse_output(self) -> None:
        d = QFileDialog.getExistingDirectory(self, "Output folder", self.output_dir.text())
        if d:
            self.output_dir.setText(d)

    def open_settings(self) -> None:
        s = self._try_collect()
        if not s:
            return
        dlg = SettingsDialog(s, self)
        if dlg.exec() == QDialog.Accepted:
            self.settings = dlg.settings
            self.settings.save()
            self._load_into_widgets()
            self._check_environment()

    # ======================================================= background ops
    def _bg(self, fn: Callable[[], Any], ok: Callable[[Any], None] | None = None,
            err: Callable[[str], None] | None = None, busy: bool = True) -> None:
        w = _Worker(fn)
        self._workers.add(w)
        if busy:
            self._busy = True
            self._update_buttons()

        def _cleanup():
            self._workers.discard(w)
            if busy:
                self._busy = False
            self._update_buttons()

        w.signals.ok.connect(lambda r: (_cleanup(), ok and ok(r)))
        w.signals.err.connect(lambda e: (_cleanup(), (err or self._show_error)(e)))
        self.pool.start(w)

    def _show_error(self, msg: str) -> None:
        log.error(msg)
        QMessageBox.critical(self, "Manhwa Recorder", msg)

    def _check_environment(self) -> None:
        def probe():
            return ff.probe(self.settings.recording.ffmpeg_path)

        def ok(caps: ff.FFmpegCaps):
            self.ffmpeg_caps = caps
            problems = []
            if not caps.gdigrab:
                problems.append("this FFmpeg build has no gdigrab (Windows screen capture)")
            if not caps.libx264:
                problems.append("this FFmpeg build has no libx264 encoder")
            self.lbl_ffmpeg.setText(("⚠ " + "; ".join(problems)) if problems else f"ready - {caps.version[:60]}")
            log.info("FFmpeg: %s (gdigrab=%s, libx264=%s)", caps.path, caps.gdigrab, caps.libx264)

        def err(msg: str):
            self.ffmpeg_caps = None
            self.lbl_ffmpeg.setText("⚠ not found")
            self._show_error(msg)
        self._bg(probe, ok, err, busy=False)

    # =============================================================== browser
    def launch_browser(self) -> None:
        s = self._try_collect()
        if not s:
            return
        b = s.browser
        self._bg(lambda: self.browser.launch(channel=b.channel, profile_dir=b.profile_dir,
                                             width=b.window_width, height=b.window_height,
                                             x=b.window_x, y=b.window_y, cdp_url=b.cdp_url),
                 ok=lambda _: self.settings.save())

    def open_chapter(self, url: Optional[str] = None, then: Callable[[], None] | None = None) -> None:
        s = self._try_collect()
        if not s:
            return
        url = url or s.project.resolved_url()
        e = validate_url(url)
        if e:
            return self._show_error(e)
        b = s.browser

        if s.recording.engine_mode == "playwright_tab" and then is not None:
            # In playwright_tab mode, recording uses its own dedicated headless Playwright tab
            # directly — no extra visible preview browser window needed!
            self.browser.current_url = url
            self.browser.adapter_name = b.adapter
            then()
            return

        def work():
            if not self.browser.is_alive():
                self.browser.launch(channel=b.channel, profile_dir=b.profile_dir,
                                    width=b.window_width, height=b.window_height,
                                    x=b.window_x, y=b.window_y, cdp_url=b.cdp_url)
            return self.browser.open(url, b.adapter, b.image_wait_timeout)

        def ok(info):
            log.info("Opened %s (%s/%s images loaded, adapter: %s)", url, info.get("loaded"),
                     info.get("total"), self.browser.adapter.name)
            if then:
                then()
        self._bg(work, ok, err=self._open_failed if self.batch.active else None)

    def _open_failed(self, msg: str) -> None:
        self.batch.mark("failed", error=msg)
        self._refresh_batch()
        self._show_error(f"Could not open chapter: {msg}\nUse 'Record this chapter' to retry, or cancel the batch.")

    def reload_chapter(self) -> None:
        self._bg(lambda: self.browser.reload(self.settings.browser.image_wait_timeout))

    def preload_images(self) -> None:
        self._bg(self.browser.preload_lazy_images,
                 ok=lambda info: log.info("Preload done: %s/%s images", info["loaded"], info["total"]))

    def _region_for(self, s: AppSettings) -> Optional[ff.Region]:
        r = s.recording
        if r.capture_mode == "desktop":
            return None
        if r.capture_mode == "region":
            return ff.Region(r.region_x, r.region_y, r.region_w, r.region_h)
        reg = self.browser.content_region()
        return ff.Region(reg.x + r.browser_offset_x, reg.y + r.browser_offset_y,
                         reg.w + r.browser_offset_w, reg.h + r.browser_offset_h)

    def test_capture(self) -> None:
        s = self._try_collect()
        if not s:
            return
        out = Path(tempfile.gettempdir()) / "manhwa_recorder_test_capture.png"

        def work():
            if s.recording.capture_mode == "browser":
                self.browser.bring_to_front()
                time.sleep(0.4)
            region = self._region_for(s)
            eng = RecordingEngine(ff.find_ffmpeg(s.recording.ffmpeg_path))
            return eng.snapshot(out, region), region

        def ok(res):
            path, region = res
            dlg = QDialog(self)
            dlg.setWindowTitle(f"Test capture - region: {region or 'full desktop'}")
            v = QVBoxLayout(dlg)
            pm = QPixmap(str(path))
            lbl = QLabel()
            lbl.setPixmap(pm.scaled(900, 700, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            v.addWidget(lbl)
            v.addWidget(QLabel(f"{pm.width()}x{pm.height()} px. If edges are off, adjust "
                               "'Browser region tweak' in Advanced settings."))
            dlg.exec()
        self._bg(work, ok)

    # ============================================================= recording
    def start_recording(self, chapter: Optional[int] = None, url: Optional[str] = None) -> None:
        if self.session and self.session.is_active:
            return self._show_error("A recording is already running.")
        s = self._try_collect()
        if not s:
            return
        if self.ffmpeg_caps is None:
            return self._show_error("FFmpeg is not available. Install it or set its path in Advanced settings.")
        s.save()
        cb = SessionCallbacks(on_state=self.bridge.state.emit, on_scroll=self.bridge.scroll.emit,
                              on_done=self.bridge.done.emit)
        sess = RecordingSession(s, self.browser, cb, chapter=chapter, url=url)
        self.session = sess
        self.progress.setValue(0)
        self.progress.setFormat("initial delay")
        self.lbl_scrolls.setText("0")

        def ok(_):
            if sess.paths:
                self.lbl_path.setText(str(sess.paths.video))

        def err(msg):
            self.session = None
            if self.batch.active:
                self.batch.mark("failed", error=msg)
                self._refresh_batch()
            self._on_state("idle")
            self._show_error(f"Could not start recording:\n{msg}")
        self._bg(sess.start, ok, err)

    def pause(self) -> None:
        if self.session and self.session.state == "recording":
            self._bg(self.session.pause)

    def resume(self) -> None:
        if self.session and self.session.state == "paused":
            sess = self.session
            self._bg(sess.resume, err=lambda m: (self._show_error(f"Resume failed: {m}"), sess.stop("resume failed")))

    def stop(self) -> None:
        if self.session and self.session.is_active:
            self.session.stop()

    def emergency_stop(self) -> None:
        self.countdown_timer.stop()
        if self.batch.active:
            self.batch.cancel()
            self.batch_info.setText("Batch cancelled by emergency stop.")
        if self.session and self.session.is_active:
            log.warning("EMERGENCY STOP")
            self.session.emergency_stop()

    def _on_hotkey(self, name: str) -> None:
        if name == "pause":
            if self.session and self.session.state == "recording":
                self.pause()
            elif self.session and self.session.state == "paused":
                self.resume()
        elif name == "stop":
            self.stop()
        elif name == "emergency":
            self.emergency_stop()

    def _on_state(self, state: str) -> None:
        self.lbl_state.setText(state)
        self._update_buttons()

    def _on_scroll(self, count: int, progress: Optional[float]) -> None:
        self.lbl_scrolls.setText(str(count))
        if progress is not None:
            self.progress.setValue(int(progress * 100))
            self.progress.setFormat(f"{progress * 100:.0f}%  ({count} scrolls)")
        else:
            self.progress.setFormat(f"{count} scrolls")

    def _on_done(self, r: dict) -> None:
        self._update_buttons()
        if r["ok"]:
            self.lbl_path.setText(r["video"])
            self.progress.setValue(100)
            self.progress.setFormat(f"done - {r['reason']}")
            log.info("Saved %s (%.1fs, %d scrolls)", r["video"], r["duration"], r["scrolls"])
        else:
            self.progress.setFormat("failed")
        if self.batch.active:
            self.batch.mark("done" if r["ok"] else "failed", output=r.get("video", ""), error=r.get("error", ""))
            self._refresh_batch()
            if r["reason"] == "emergency stop":
                self.batch.cancel()
            else:
                return self._batch_next()
        if not r["ok"]:
            self._show_error(f"Recording failed: {r['error']}")

    def _tick(self) -> None:
        s = self.session
        if s and s.recorder:
            e = int(s.elapsed)
            self.lbl_elapsed.setText(f"{e // 3600:02d}:{e % 3600 // 60:02d}:{e % 60:02d}" if e >= 3600
                                     else f"{e // 60:02d}:{e % 60:02d}")
            self.lbl_size.setText(human_size(s.size_bytes))
            if s.is_active:
                self.lbl_ffmpeg.setText(s.ffmpeg_status)
                if s.scroller and s.scroller.progress is None:
                    self.progress.setFormat(f"{s.scroller.state.value} - {s.scroller.count} scrolls")

    def _update_buttons(self) -> None:
        st = self.session.state if self.session else "idle"
        active = bool(self.session and self.session.is_active)
        busy = self._busy
        self.btn_start.setEnabled(not active and not busy and not self.batch.active)
        self.btn_pause.setEnabled(st == "recording" and not busy)
        self.btn_resume.setEnabled(st == "paused" and not busy)
        self.btn_stop.setEnabled(st in ("recording", "paused"))
        self.btn_emergency.setEnabled(active or self.batch.active)
        for b in (self.btn_launch, self.btn_open, self.btn_reload, self.btn_preload, self.btn_test_capture):
            b.setEnabled(not active and not busy)
        self.btn_settings.setEnabled(not active)
        self.btn_batch_start.setEnabled(not active and not busy and not self.batch.active and bool(self.batch.items))
        self.btn_batch_next.setEnabled(self.batch.active and not active and not busy and self.batch.current is not None)
        self.btn_batch_cancel.setEnabled(self.batch.active)
        self.btn_batch_package.setEnabled(not active and not busy and bool(self.batch.items))
        self.btn_batch_publish.setEnabled(True)
        for b in (self.btn_batch_add, self.btn_batch_remove, self.btn_batch_clear):
            b.setEnabled(not self.batch.active)

    def open_output_folder(self) -> None:
        target = Path(self.lbl_path.text()).parent if self.lbl_path.text() not in ("", "-") \
            else Path(self.output_dir.text())
        if not target.exists():
            target = Path(self.output_dir.text())
        target.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(target)))

    # ================================================================= batch
    def _refresh_batch(self) -> None:
        self.batch_list.clear()
        icons = {"pending": "○", "ready": "◐", "recording": "●", "done": "✔", "failed": "✖", "skipped": "–"}
        for i, it in enumerate(self.batch.items):
            text = f"{icons.get(it.status, '?')}  Chapter {it.chapter}  [{it.status}]  {it.url}"
            if it.error:
                text += f"  — {it.error[:80]}"
            item = QListWidgetItem(text)
            if self.batch.active and i == self.batch.index:
                item.setForeground(Qt.yellow)
            self.batch_list.addItem(item)
        self._update_buttons()

    def batch_add(self) -> None:
        dlg = ChapterDialog(self.url_template.text(), self)
        if dlg.exec() == QDialog.Accepted:
            existing = {i.chapter for i in self.batch.items}
            self.batch.items += [i for i in dlg.items if i.chapter not in existing]
            self.batch.items.sort(key=lambda i: i.chapter)
            self._refresh_batch()

    def batch_remove(self) -> None:
        rows = sorted({i.row() for i in self.batch_list.selectedIndexes()}, reverse=True)
        for r in rows:
            del self.batch.items[r]
        self._refresh_batch()

    def batch_clear(self) -> None:
        self.batch.items.clear()
        self._refresh_batch()

    def batch_start(self) -> None:
        if not self._try_collect():
            return
        for it in self.batch.items:
            if it.status != "done":
                it.status, it.error = "pending", ""
        item = self.batch.start()
        if item is None:
            self.batch_info.setText("Nothing left to record (all chapters done).")
            return self._refresh_batch()
        self._batch_open(item)

    def _batch_open(self, item) -> None:
        self._refresh_batch()
        self.batch_info.setText(f"Opening chapter {item.chapter}…")

        def ready():
            item.status = "ready"
            self._refresh_batch()
            bs = self.settings.batch
            delay = int(bs.auto_continue_delay) if bs.auto_continue and bs.auto_continue_delay > 0 else 1
            self._countdown = delay
            self.batch_info.setText(f"Chapter {item.chapter} ready. Auto-recording in {self._countdown}s "
                                    "(Cancel batch to abort).")
            self.countdown_timer.start()
        self.open_chapter(item.url, then=ready)

    def _countdown_tick(self) -> None:
        if not self.batch.active:
            return self.countdown_timer.stop()
        self._countdown -= 1
        if self._countdown <= 0:
            self.countdown_timer.stop()
            self.batch_record_current()
        else:
            cur = self.batch.current
            self.batch_info.setText(f"Chapter {cur.chapter if cur else '?'} ready. Auto-starting in "
                                    f"{self._countdown}s (Cancel batch to abort).")

    def batch_record_current(self) -> None:
        self.countdown_timer.stop()
        item = self.batch.current
        if not item:
            return
        item.status, item.error = "recording", ""
        self._refresh_batch()
        self.batch_info.setText(f"Recording chapter {item.chapter}…")
        self.start_recording(chapter=item.chapter, url=item.url)

    def _batch_next(self) -> None:
        nxt = self.batch.advance()
        if nxt is None:
            self.batch_info.setText(f"Batch finished: {self.batch.summary()}")
            self._refresh_batch()
            self.batch_package(auto=True)
            return
        self._batch_open(nxt)

    def batch_package(self, auto: bool = False) -> None:
        """Gather all batch episodes into one folder (chaptersXtoY) and generate all .md files."""
        chapters = [it.chapter for it in self.batch.items if it.status == "done"]
        if not chapters:
            chapters = [it.chapter for it in self.batch.items]
        if not chapters:
            if not auto:
                self._show_error("No chapters found in batch to package.")
            return

        try:
            from ..core.batch_packager import BatchPackager
            out_root = Path(self.output_dir.text().strip()) if self.output_dir.text().strip() \
                else Path(self.settings.project.output_dir)
            series_name = self.series.text().strip() or self.settings.project.series_name
            packager = BatchPackager(
                series_name=series_name,
                chapters=chapters,
                output_root=out_root,
            )
            pkg_path = packager.package()
            msg = f"Batch packaged into '{pkg_path.name}'! All .md files ready. Next: use manhwa-publisher."
            self.batch_info.setText(msg)
            log.info("Batch packaged successfully: %s", pkg_path)
            if not auto:
                QMessageBox.information(
                    self,
                    "Batch Packaged",
                    f"Successfully packaged {len(chapters)} chapter(s) into:\n{pkg_path}\n\n"
                    f"All pipeline .md files (including readme.md) and youtube_publishing_metadata.json are ready.\n\n"
                    f"Next step:\nUse 'manhwa-publisher' CLI to validate and publish to YouTube."
                )
        except Exception as e:
            log.exception("Error packaging batch")
            if not auto:
                self._show_error(f"Failed to package batch: {e}")

    def open_manhwa_publisher(self) -> None:
        """Show CLI usage commands for publishing with manhwa-publisher."""
        publisher_dir = Path(__file__).resolve().parents[3] / "manhwa-publisher"
        chapters = [it.chapter for it in self.batch.items]
        if chapters:
            start_ch, end_ch = min(chapters), max(chapters)
            folder_name = f"chapters{start_ch}to{end_ch}" if start_ch != end_ch else f"chapter{start_ch}"
            ch_str = f"Ch{start_ch}_Ch{end_ch}" if start_ch != end_ch else f"Ch{start_ch}"
        else:
            folder_name = "chaptersXtoY"
            ch_str = "ChX_ChY"

        QMessageBox.information(
            self,
            "Manhwa Publisher CLI",
            f"Manhwa Publisher is located at:\n{publisher_dir}\n\n"
            f"To validate and publish your packaged video, run in PowerShell:\n\n"
            f'cd "{publisher_dir}"\n'
            f'.\\.venv\\Scripts\\manhwa-publisher doctor\n\n'
            f'.\\.venv\\Scripts\\manhwa-publisher validate `\n'
            f'  --video "..\\{folder_name}\\SSS_Class_Suicide_Hunter_{ch_str}_Master.mp4" `\n'
            f'  --metadata "..\\{folder_name}\\youtube_publishing_metadata.json"\n\n'
            f'.\\.venv\\Scripts\\manhwa-publisher publish `\n'
            f'  --video "..\\{folder_name}\\SSS_Class_Suicide_Hunter_{ch_str}_Master.mp4" `\n'
            f'  --metadata "..\\{folder_name}\\youtube_publishing_metadata.json" `\n'
            f'  --approve'
        )

    def batch_cancel(self) -> None:
        self.countdown_timer.stop()
        self.batch.cancel()
        self.batch_info.setText("Batch cancelled. A running recording continues until you stop it.")
        self._refresh_batch()

    # ============================================================== shutdown
    def closeEvent(self, event) -> None:
        if self.session and self.session.is_active:
            if QMessageBox.question(self, "Recording in progress",
                                    "A recording is running. Stop it, save the video and quit?") != QMessageBox.Yes:
                event.ignore()
                return
            log.info("Closing: finalizing recording")
            self.session._finish("application closing", False)
        try:
            self._collect().save()
        except Exception:
            self.settings.save()
        self.timer.stop()
        self.hotkeys.stop()
        self.browser.close()
        logging.getLogger().removeHandler(self._log_handler)
        event.accept()
