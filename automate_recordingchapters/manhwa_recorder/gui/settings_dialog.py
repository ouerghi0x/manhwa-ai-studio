"""Advanced settings dialog (capture, encoding, browser, scrolling details)."""
from __future__ import annotations

from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QDialogButtonBox, QDoubleSpinBox,
                               QFileDialog, QFormLayout, QGroupBox, QHBoxLayout, QLineEdit,
                               QMessageBox, QPushButton, QSpinBox, QVBoxLayout, QWidget)

from ..config.settings import X264_PRESETS, AppSettings
from ..core.site_adapters import adapter_names


def _spin(lo: int, hi: int, val: int) -> QSpinBox:
    s = QSpinBox()
    s.setRange(lo, hi)
    s.setValue(val)
    return s


def _dspin(lo: float, hi: float, val: float, step: float = 0.5) -> QDoubleSpinBox:
    s = QDoubleSpinBox()
    s.setRange(lo, hi)
    s.setSingleStep(step)
    s.setDecimals(2)
    s.setValue(val)
    return s


class SettingsDialog(QDialog):
    def __init__(self, settings: AppSettings, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Advanced settings")
        self.setMinimumWidth(520)
        self.settings = settings
        r, b, sc, bt = settings.recording, settings.browser, settings.scroll, settings.batch
        lay = QVBoxLayout(self)

        # Encoding / capture
        g = QGroupBox("Capture & encoding")
        f = QFormLayout(g)
        self.engine_mode = QComboBox()
        self.engine_mode.addItems(["playwright_tab", "screen_capture"])
        self.engine_mode.setCurrentText(r.engine_mode)
        self.engine_mode.setToolTip("playwright_tab: Records only the browser tab in background (no desktop, zero interference).\nscreen_capture: Records via FFmpeg Windows screen capture.")
        f.addRow("Recording Engine", self.engine_mode)
        self.preset = QComboBox()
        self.preset.addItems(X264_PRESETS)
        self.preset.setCurrentText(r.preset)
        f.addRow("x264 preset", self.preset)
        self.capture_mode = QComboBox()
        self.capture_mode.addItems(["browser", "desktop", "region"])
        self.capture_mode.setCurrentText(r.capture_mode)
        f.addRow("Capture mode", self.capture_mode)
        self.crop_mode = QComboBox()
        self.crop_mode.addItems(["auto_comic", "none", "custom"])
        self.crop_mode.setCurrentText(r.crop_mode)
        self.crop_mode.setToolTip("auto_comic: automatically crops black side margins and centers the manhwa strip.")
        f.addRow("Crop to Comic", self.crop_mode)
        self.hide_clutter = QCheckBox("Hide floating headers, navbars and clutter")
        self.hide_clutter.setChecked(r.hide_clutter)
        f.addRow("", self.hide_clutter)
        self.off = [_spin(-500, 500, v) for v in (r.browser_offset_x, r.browser_offset_y,
                                                  r.browser_offset_w, r.browser_offset_h)]
        row = QHBoxLayout()
        for w in self.off:
            row.addWidget(w)
        f.addRow("Browser region tweak x/y/w/h", self._wrap(row))
        self.reg = [_spin(-10000, 10000, r.region_x), _spin(-10000, 10000, r.region_y),
                    _spin(16, 10000, r.region_w), _spin(16, 10000, r.region_h)]
        row = QHBoxLayout()
        for w in self.reg:
            row.addWidget(w)
        f.addRow("Custom region x/y/w/h", self._wrap(row))
        self.draw_mouse = QCheckBox("Record mouse cursor")
        self.draw_mouse.setChecked(r.draw_mouse)
        f.addRow("", self.draw_mouse)
        self.ffmpeg_path = QLineEdit(r.ffmpeg_path)
        self.ffmpeg_path.setPlaceholderText("empty = use ffmpeg from PATH")
        btn = QPushButton("Browse…")
        btn.clicked.connect(self._browse_ffmpeg)
        row = QHBoxLayout()
        row.addWidget(self.ffmpeg_path)
        row.addWidget(btn)
        f.addRow("FFmpeg path", self._wrap(row))
        lay.addWidget(g)

        # Browser
        g = QGroupBox("Browser")
        f = QFormLayout(g)
        self.channel = QComboBox()
        self.channel.addItems(["chrome", "msedge"])
        self.channel.setCurrentText(b.channel)
        f.addRow("Browser", self.channel)
        self.win = [_spin(400, 7680, b.window_width), _spin(300, 4320, b.window_height),
                    _spin(-10000, 10000, b.window_x), _spin(-10000, 10000, b.window_y)]
        row = QHBoxLayout()
        for w in self.win:
            row.addWidget(w)
        f.addRow("Window w/h/x/y", self._wrap(row))
        self.profile_dir = QLineEdit(b.profile_dir)
        f.addRow("Profile folder", self.profile_dir)
        self.cdp_url = QLineEdit(b.cdp_url)
        self.cdp_url.setPlaceholderText("optional, e.g. http://localhost:9222 (existing browser)")
        f.addRow("Attach via CDP", self.cdp_url)
        self.adapter = QComboBox()
        self.adapter.addItems(adapter_names())
        self.adapter.setCurrentText(b.adapter)
        f.addRow("Site adapter", self.adapter)
        self.img_timeout = _dspin(0, 300, b.image_wait_timeout, 1)
        f.addRow("Image wait timeout (s)", self.img_timeout)
        lay.addWidget(g)

        # Scrolling
        g = QGroupBox("Scrolling & batch")
        f = QFormLayout(g)
        self.max_scrolls = _spin(1, 100000, sc.max_scrolls)
        f.addRow("Max scroll actions", self.max_scrolls)
        self.end_detection = QCheckBox("Detect end of chapter (scroll position / page height)")
        self.end_detection.setChecked(sc.end_detection)
        f.addRow("", self.end_detection)
        self.end_conf = _spin(1, 50, sc.end_confirmations)
        f.addRow("End confirmations", self.end_conf)
        self.stall = _spin(2, 500, sc.stall_limit)
        f.addRow("Stall limit (no movement)", self.stall)
        self.end_hold = _dspin(0, 60, sc.end_hold)
        f.addRow("Hold at end (s)", self.end_hold)
        self.backend = QComboBox()
        self.backend.addItems(["playwright", "pyautogui"])
        self.backend.setCurrentText(sc.key_backend)
        self.backend.setToolTip("playwright: keys go straight to the page (focus not required).\n"
                                "pyautogui: real OS key presses (browser must have focus).")
        f.addRow("Key backend", self.backend)
        self.auto_continue = QCheckBox("Batch: start next chapter automatically")
        self.auto_continue.setChecked(bt.auto_continue)
        f.addRow("", self.auto_continue)
        self.auto_delay = _dspin(0, 600, bt.auto_continue_delay, 1)
        f.addRow("Auto-continue countdown (s)", self.auto_delay)
        lay.addWidget(g)

        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(self._accept)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)

    @staticmethod
    def _wrap(layout) -> QWidget:
        w = QWidget()
        layout.setContentsMargins(0, 0, 0, 0)
        w.setLayout(layout)
        return w

    def _browse_ffmpeg(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Locate ffmpeg.exe", "", "ffmpeg (ffmpeg.exe)")
        if path:
            self.ffmpeg_path.setText(path)

    def _accept(self) -> None:
        data = self.settings.model_dump()
        r, b, sc, bt = data["recording"], data["browser"], data["scroll"], data["batch"]
        r.update(engine_mode=self.engine_mode.currentText(), preset=self.preset.currentText(),
                 capture_mode=self.capture_mode.currentText(),
                 crop_mode=self.crop_mode.currentText(), hide_clutter=self.hide_clutter.isChecked(),
                 browser_offset_x=self.off[0].value(), browser_offset_y=self.off[1].value(),
                 browser_offset_w=self.off[2].value(), browser_offset_h=self.off[3].value(),
                 region_x=self.reg[0].value(), region_y=self.reg[1].value(),
                 region_w=self.reg[2].value(), region_h=self.reg[3].value(),
                 draw_mouse=self.draw_mouse.isChecked(), ffmpeg_path=self.ffmpeg_path.text().strip())
        b.update(channel=self.channel.currentText(), window_width=self.win[0].value(),
                 window_height=self.win[1].value(), window_x=self.win[2].value(),
                 window_y=self.win[3].value(), profile_dir=self.profile_dir.text().strip(),
                 cdp_url=self.cdp_url.text().strip(), adapter=self.adapter.currentText(),
                 image_wait_timeout=self.img_timeout.value())
        sc.update(max_scrolls=self.max_scrolls.value(), end_detection=self.end_detection.isChecked(),
                  end_confirmations=self.end_conf.value(), stall_limit=self.stall.value(),
                  end_hold=self.end_hold.value(), key_backend=self.backend.currentText())
        bt.update(auto_continue=self.auto_continue.isChecked(),
                  auto_continue_delay=self.auto_delay.value())
        try:
            self.settings = AppSettings.model_validate(data)
        except Exception as exc:
            QMessageBox.warning(self, "Invalid settings", str(exc))
            return
        self.accept()
