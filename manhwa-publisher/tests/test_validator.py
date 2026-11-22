"""Unit tests for FFprobe video validation and Pillow thumbnail validation."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image

from publisher.core.validator import VideoProbeInfo, validate_thumbnail, validate_video


class TestValidator(unittest.TestCase):
    def test_missing_video_is_blocking_error(self) -> None:
        res = validate_video(Path("nonexistent_video_12345.mp4"))
        self.assertFalse(res.valid)
        self.assertTrue(any("does not exist" in e for e in res.errors))

    def test_empty_video_is_blocking_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vid = Path(tmp) / "empty.mp4"
            vid.write_bytes(b"")
            res = validate_video(vid)
            self.assertFalse(res.valid)
            self.assertTrue(any("empty" in e.lower() for e in res.errors))

    def test_short_landscape_warns_but_does_not_block(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vid = Path(tmp) / "clip.mp4"
            vid.write_bytes(b"fake mp4 data")
            fake_probe = VideoProbeInfo(
                file_size_bytes=13,
                duration_seconds=210.0,
                width=1920,
                height=1080,
                video_codec="h264",
                audio_codec="aac",
                has_audio=True,
                format_name="mp4",
            )
            with patch("publisher.core.validator.probe_video", return_value=fake_probe):
                res = validate_video(vid, expected_type="short")
            self.assertTrue(res.valid)
            self.assertEqual(res.errors, [])
            self.assertGreaterEqual(len(res.warnings), 2)

    def test_valid_thumbnail_passes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            thumb = Path(tmp) / "thumb.jpg"
            img = Image.new("RGB", (1280, 720), color=(30, 60, 90))
            img.save(thumb, format="JPEG")
            errors, warnings, info = validate_thumbnail(thumb)
            self.assertEqual(errors, [])
            self.assertEqual(warnings, [])
            self.assertIsNotNone(info)
            assert info is not None
            self.assertEqual(info.width, 1280)
            self.assertEqual(info.height, 720)
            self.assertEqual(info.image_format, "JPEG")

    def test_small_thumbnail_warns_without_blocking(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            thumb = Path(tmp) / "small.png"
            img = Image.new("RGB", (320, 180), color=(10, 20, 30))
            img.save(thumb, format="PNG")
            errors, warnings, info = validate_thumbnail(thumb)
            self.assertEqual(errors, [])
            self.assertEqual(len(warnings), 1)
            self.assertIsNotNone(info)

    def test_corrupted_thumbnail_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            thumb = Path(tmp) / "bad.jpg"
            thumb.write_bytes(b"not an image")
            errors, _, _ = validate_thumbnail(thumb)
            self.assertTrue(len(errors) >= 1)


if __name__ == "__main__":
    unittest.main()
