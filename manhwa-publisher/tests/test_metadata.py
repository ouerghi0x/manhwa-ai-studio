"""Unit tests for metadata JSON contract parsing and validation."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from zoneinfo import ZoneInfo

from publisher.core.metadata import (
    MetadataValidationError,
    load_metadata,
    validate_metadata_dict,
)


class TestMetadataValidation(unittest.TestCase):
    def test_valid_full_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            meta_file = Path(tmp) / "video.json"
            payload = {
                "title": "SSS-Class Suicide Hunter - Chapter 7",
                "description": "The story continues...",
                "tags": ["manhwa", "sss class suicide hunter", "webtoon"],
                "category_id": "24",
                "language": "en",
                "type": "long",
                "thumbnail": "thumb.jpg",
                "playlist_id": "PL12345",
                "visibility": "private",
                "publish_at": "2026-11-25T20:00:00+01:00",
            }
            meta_file.write_text(json.dumps(payload), encoding="utf-8")

            meta = load_metadata(meta_file, default_tz=ZoneInfo("Africa/Tunis"))
            self.assertEqual(meta.title, "SSS-Class Suicide Hunter - Chapter 7")
            self.assertEqual(meta.video_type, "long")
            self.assertEqual(meta.tags, ["manhwa", "sss class suicide hunter", "webtoon"])
            self.assertEqual(meta.playlist_id, "PL12345")
            self.assertIsNotNone(meta.publish_at)
            self.assertIsNotNone(meta.publish_at.tzinfo)  # type: ignore[union-attr]

    def test_minimal_required_fields_only(self) -> None:
        meta = validate_metadata_dict({"title": "Short Clip", "type": "short"})
        self.assertEqual(meta.title, "Short Clip")
        self.assertEqual(meta.video_type, "short")
        self.assertEqual(meta.visibility, "private")
        self.assertEqual(meta.category_id, "24")
        self.assertIsNone(meta.publish_at)

    def test_missing_required_fields_raises(self) -> None:
        with self.assertRaises(MetadataValidationError) as ctx:
            validate_metadata_dict({"description": "No title or type"})
        self.assertGreaterEqual(len(ctx.exception.errors), 2)

    def test_invalid_type_and_visibility_raises(self) -> None:
        with self.assertRaises(MetadataValidationError) as ctx:
            validate_metadata_dict(
                {"title": "Test", "type": "reel", "visibility": "friends"}
            )
        self.assertEqual(len(ctx.exception.errors), 2)

    def test_title_too_long_raises(self) -> None:
        with self.assertRaises(MetadataValidationError):
            validate_metadata_dict({"title": "A" * 101, "type": "long"})

    def test_invalid_publish_at_raises(self) -> None:
        with self.assertRaises(MetadataValidationError):
            validate_metadata_dict(
                {"title": "Test", "type": "long", "publish_at": "not-a-date"}
            )

    def test_invalid_json_file_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            meta_file = Path(tmp) / "broken.json"
            meta_file.write_text("{bad json", encoding="utf-8")
            with self.assertRaises(MetadataValidationError):
                load_metadata(meta_file)


if __name__ == "__main__":
    unittest.main()
