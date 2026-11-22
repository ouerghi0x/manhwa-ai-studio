"""Automatic video and thumbnail validation using FFprobe and Pillow."""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from PIL import Image, UnidentifiedImageError

MAX_THUMBNAIL_BYTES = 2 * 1024 * 1024  # YouTube 2 MB thumbnail limit
SUPPORTED_THUMBNAIL_FORMATS = frozenset({"JPEG", "PNG", "GIF", "BMP"})
MIN_THUMBNAIL_WIDTH = 640
YOUTUBE_MAX_FILE_BYTES = 256 * 1024 * 1024 * 1024  # 256 GB
SHORT_MAX_DURATION_SECONDS = 180.0  # YouTube Shorts up to 3 minutes


@dataclass
class VideoProbeInfo:
    """Extracted technical metadata from FFprobe."""

    file_size_bytes: int
    duration_seconds: float | None = None
    width: int | None = None
    height: int | None = None
    video_codec: str | None = None
    audio_codec: str | None = None
    has_audio: bool = False
    format_name: str | None = None

    @property
    def aspect_ratio(self) -> float | None:
        if self.width and self.height and self.height > 0:
            return round(self.width / self.height, 4)
        return None

    def to_dict(self) -> dict[str, Any]:
        return {
            "file_size_bytes": self.file_size_bytes,
            "duration_seconds": self.duration_seconds,
            "width": self.width,
            "height": self.height,
            "aspect_ratio": self.aspect_ratio,
            "video_codec": self.video_codec,
            "audio_codec": self.audio_codec,
            "has_audio": self.has_audio,
            "format_name": self.format_name,
        }


@dataclass
class ThumbnailInfo:
    """Extracted technical metadata from a thumbnail image."""

    file_size_bytes: int
    image_format: str | None = None
    width: int | None = None
    height: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "file_size_bytes": self.file_size_bytes,
            "image_format": self.image_format,
            "width": self.width,
            "height": self.height,
        }


@dataclass
class ValidationResult:
    """Structured validation outcome separating blocking errors from warnings."""

    valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    video_info: VideoProbeInfo | None = None
    thumbnail_info: ThumbnailInfo | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "errors": list(self.errors),
            "warnings": list(self.warnings),
            "video_info": self.video_info.to_dict() if self.video_info else None,
            "thumbnail_info": self.thumbnail_info.to_dict() if self.thumbnail_info else None,
        }


def check_ffprobe_available() -> str | None:
    """Return the path to ffprobe if available on PATH, else None."""
    return shutil.which("ffprobe")


def probe_video(video_path: Path) -> VideoProbeInfo:
    """Run FFprobe on a video file and return structured stream info."""
    ffprobe_bin = check_ffprobe_available()
    if not ffprobe_bin:
        raise RuntimeError(
            "ffprobe executable not found on PATH. Install FFmpeg and add it to PATH."
        )

    cmd = [
        ffprobe_bin,
        "-v",
        "error",
        "-print_format",
        "json",
        "-show_format",
        "-show_streams",
        str(video_path),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        stderr = proc.stderr.strip() or "Unknown ffprobe error"
        raise ValueError(f"FFprobe failed to inspect video (possibly corrupted): {stderr}")

    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise ValueError(f"FFprobe returned unreadable JSON: {exc}") from exc

    streams = payload.get("streams") or []
    fmt = payload.get("format") or {}

    video_stream = next((s for s in streams if s.get("codec_type") == "video"), None)
    audio_stream = next((s for s in streams if s.get("codec_type") == "audio"), None)

    duration: float | None = None
    raw_duration = fmt.get("duration") or (video_stream.get("duration") if video_stream else None)
    if raw_duration is not None:
        try:
            duration = round(float(raw_duration), 3)
        except (TypeError, ValueError):
            duration = None

    width = int(video_stream["width"]) if video_stream and video_stream.get("width") else None
    height = int(video_stream["height"]) if video_stream and video_stream.get("height") else None

    return VideoProbeInfo(
        file_size_bytes=video_path.stat().st_size,
        duration_seconds=duration,
        width=width,
        height=height,
        video_codec=video_stream.get("codec_name") if video_stream else None,
        audio_codec=audio_stream.get("codec_name") if audio_stream else None,
        has_audio=audio_stream is not None,
        format_name=fmt.get("format_name"),
    )


def validate_video(
    video_path: Path,
    *,
    expected_type: str = "long",
    thumbnail_path: Path | None = None,
) -> ValidationResult:
    """Validate video file and optional thumbnail.

    Blocking errors prevent upload; warnings are reported without blocking.
    """
    errors: list[str] = []
    warnings: list[str] = []
    video_info: VideoProbeInfo | None = None
    thumbnail_info: ThumbnailInfo | None = None

    if not video_path.exists():
        errors.append(f"Video file does not exist: {video_path}")
    elif not video_path.is_file():
        errors.append(f"Video path is not a file: {video_path}")
    else:
        file_size = video_path.stat().st_size
        if file_size == 0:
            errors.append(f"Video file is empty (0 bytes): {video_path}")
        elif file_size > YOUTUBE_MAX_FILE_BYTES:
            errors.append(f"Video file exceeds YouTube 256 GB limit ({file_size} bytes).")
        else:
            try:
                video_info = probe_video(video_path)
            except (RuntimeError, ValueError) as exc:
                errors.append(str(exc))

    if video_info is not None:
        if not video_info.video_codec:
            errors.append("No video stream detected in file.")
        if not video_info.width or not video_info.height:
            errors.append("Could not determine video resolution.")
        if video_info.duration_seconds is None or video_info.duration_seconds <= 0:
            errors.append("Video duration is missing or zero.")
        if not video_info.has_audio:
            warnings.append("No audio stream detected in video.")

        # Advisory checks for Shorts vs Long-form (never blocking — YouTube decides final type)
        if expected_type == "short":
            if (
                video_info.duration_seconds is not None
                and video_info.duration_seconds > SHORT_MAX_DURATION_SECONDS
            ):
                warnings.append(
                    f"Video declared as 'short' has duration {video_info.duration_seconds:.1f}s "
                    f"(> {SHORT_MAX_DURATION_SECONDS:.0f}s); YouTube may classify it as long-form."
                )
            if video_info.width and video_info.height and video_info.width > video_info.height:
                warnings.append(
                    f"Video declared as 'short' is landscape ({video_info.width}x{video_info.height}); "
                    "YouTube Shorts typically use vertical (9:16) or square (1:1) aspect ratios."
                )
        elif expected_type == "long":
            if video_info.width and video_info.height and video_info.height > video_info.width:
                warnings.append(
                    f"Video declared as 'long' is vertical ({video_info.width}x{video_info.height}); "
                    "YouTube may classify short vertical videos as Shorts."
                )

    if thumbnail_path is not None:
        thumb_errors, thumb_warnings, thumbnail_info = validate_thumbnail(thumbnail_path)
        errors.extend(thumb_errors)
        warnings.extend(thumb_warnings)

    return ValidationResult(
        valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
        video_info=video_info,
        thumbnail_info=thumbnail_info,
    )


def validate_thumbnail(
    thumbnail_path: Path,
) -> tuple[list[str], list[str], ThumbnailInfo | None]:
    """Validate a custom YouTube thumbnail image."""
    errors: list[str] = []
    warnings: list[str] = []

    if not thumbnail_path.exists():
        return ([f"Thumbnail file does not exist: {thumbnail_path}"], warnings, None)
    if not thumbnail_path.is_file():
        return ([f"Thumbnail path is not a file: {thumbnail_path}"], warnings, None)

    size_bytes = thumbnail_path.stat().st_size
    if size_bytes == 0:
        return ([f"Thumbnail file is empty: {thumbnail_path}"], warnings, None)
    if size_bytes > MAX_THUMBNAIL_BYTES:
        errors.append(
            f"Thumbnail exceeds YouTube 2 MB limit ({size_bytes / (1024 * 1024):.2f} MB)."
        )

    try:
        with Image.open(thumbnail_path) as img:
            img_format = (img.format or "").upper()
            width, height = img.size
            img.verify()
    except (UnidentifiedImageError, OSError) as exc:
        return ([f"Invalid or corrupted thumbnail image: {exc}"], warnings, None)

    if img_format not in SUPPORTED_THUMBNAIL_FORMATS:
        errors.append(
            f"Unsupported thumbnail format {img_format!r}. "
            f"Supported: {sorted(SUPPORTED_THUMBNAIL_FORMATS)}."
        )

    if width < MIN_THUMBNAIL_WIDTH:
        warnings.append(
            f"Thumbnail width ({width}px) is below YouTube's recommended minimum of "
            f"{MIN_THUMBNAIL_WIDTH}px."
        )

    info = ThumbnailInfo(
        file_size_bytes=size_bytes,
        image_format=img_format,
        width=width,
        height=height,
    )
    return (errors, warnings, info)
