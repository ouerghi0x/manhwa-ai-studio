"""Validated application configuration (Pydantic)."""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

log = logging.getLogger(__name__)

PACKAGE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_SETTINGS_FILE = PACKAGE_DIR / "config" / "user_settings.json"

ScrollKey = Literal["PageDown", "ArrowDown", "Space"]
ScrollProfile = Literal["Slow", "Normal", "Fast", "Custom"]
SCROLL_PROFILES: dict[str, float] = {"Slow": 4.0, "Normal": 2.5, "Fast": 1.5}
X264_PRESETS = ["ultrafast", "superfast", "veryfast", "faster", "fast",
                "medium", "slow", "slower", "veryslow"]


class ProjectSettings(BaseModel):
    series_name: str = "SSS-Class Suicide Hunter"
    chapter_number: int = Field(7, ge=0, le=100000)
    url_template: str = "https://asurascans.com/comics/sss-class-suicide-hunter-7ba78ec7/chapter/{chapter}"
    chapter_url: str = ""
    output_dir: str = str(PACKAGE_DIR / "output")
    filename: str = ""  # empty -> chapter-007

    @field_validator("series_name")
    @classmethod
    def _series_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Series name must not be empty")
        return v.strip()

    def resolved_url(self) -> str:
        if self.chapter_url.strip():
            return self.chapter_url.strip()
        if "{chapter}" in self.url_template:
            return self.url_template.format(chapter=self.chapter_number)
        return self.url_template.strip()


class RecordingSettings(BaseModel):
    width: int = Field(1920, ge=320, le=7680)
    height: int = Field(1080, ge=240, le=4320)
    fps: int = Field(30, ge=1, le=120)
    crf: int = Field(18, ge=0, le=51)
    preset: str = "veryfast"
    container: Literal["mp4", "mkv"] = "mp4"
    engine_mode: Literal["playwright_tab", "screen_capture"] = "playwright_tab"
    capture_mode: Literal["browser", "desktop", "region"] = "browser"
    crop_mode: Literal["auto_comic", "none", "custom"] = "auto_comic"
    crop_x: int = 0
    crop_y: int = 0
    crop_w: int = 0
    crop_h: int = 0
    hide_clutter: bool = True  # hide floating headers, sticky bars, ads
    region_x: int = 0
    region_y: int = 0
    region_w: int = Field(1920, ge=16)
    region_h: int = Field(1080, ge=16)
    # Pixel fine-tuning applied to the auto-detected browser region.
    browser_offset_x: int = 0
    browser_offset_y: int = 0
    browser_offset_w: int = 0
    browser_offset_h: int = 0
    draw_mouse: bool = False
    ffmpeg_path: str = ""  # empty -> search PATH

    @field_validator("preset")
    @classmethod
    def _preset_valid(cls, v: str) -> str:
        if v not in X264_PRESETS:
            raise ValueError(f"Invalid x264 preset '{v}'")
        return v

    @model_validator(mode="after")
    def _even_size(self):
        if self.width % 2 or self.height % 2:
            raise ValueError("Output width and height must be even numbers (H.264 requirement)")
        return self


class ScrollSettings(BaseModel):
    key: ScrollKey = "PageDown"
    profile: ScrollProfile = "Normal"
    delay: float = Field(2.5, ge=0.1, le=120)
    initial_delay: float = Field(5.0, ge=0, le=600)
    max_scrolls: int = Field(2000, ge=1, le=100000)
    end_detection: bool = True
    end_confirmations: int = Field(3, ge=1, le=50)
    stall_limit: int = Field(15, ge=2, le=500)
    end_hold: float = Field(3.0, ge=0, le=60)
    key_backend: Literal["playwright", "pyautogui"] = "playwright"

    def effective_delay(self) -> float:
        return SCROLL_PROFILES.get(self.profile, self.delay) if self.profile != "Custom" else self.delay


class BrowserSettings(BaseModel):
    channel: Literal["chrome", "msedge"] = "chrome"
    profile_dir: str = str(PACKAGE_DIR / "browser_profile")
    window_width: int = Field(1280, ge=400, le=7680)
    window_height: int = Field(1000, ge=300, le=4320)
    window_x: int = 0
    window_y: int = 0
    cdp_url: str = ""  # e.g. http://localhost:9222 to attach to an existing browser
    adapter: str = "auto"
    image_wait_timeout: float = Field(20.0, ge=0, le=300)


class BatchSettings(BaseModel):
    auto_continue: bool = False
    auto_continue_delay: float = Field(10.0, ge=0, le=600)


class AppSettings(BaseModel):
    project: ProjectSettings = ProjectSettings()
    recording: RecordingSettings = RecordingSettings()
    scroll: ScrollSettings = ScrollSettings()
    browser: BrowserSettings = BrowserSettings()
    batch: BatchSettings = BatchSettings()

    @classmethod
    def load(cls, path: Path | str = DEFAULT_SETTINGS_FILE) -> "AppSettings":
        p = Path(path)
        if p.exists():
            try:
                return cls.model_validate(json.loads(p.read_text(encoding="utf-8")))
            except Exception as exc:  # corrupt or outdated -> defaults
                log.warning("Could not load settings from %s (%s); using defaults", p, exc)
        return cls()

    def save(self, path: Path | str = DEFAULT_SETTINGS_FILE) -> None:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(self.model_dump_json(indent=2), encoding="utf-8")
