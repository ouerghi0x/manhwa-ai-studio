"""Unit tests for the full publishing pipeline and partial-failure recovery."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from PIL import Image

from publisher.config import AppConfig, DatabaseConfig, PathsConfig, SafetyConfig, UploadConfig
from publisher.core.pipeline import PublishingPipeline
from publisher.core.validator import VideoProbeInfo
from publisher.database.models import JobStatus, OperationStatus, OperationType
from publisher.database.repository import JobRepository
from publisher.exit_codes import ExitCode


def _fake_probe() -> VideoProbeInfo:
    return VideoProbeInfo(
        file_size_bytes=1024,
        duration_seconds=120.0,
        width=1920,
        height=1080,
        video_codec="h264",
        audio_codec="aac",
        has_audio=True,
        format_name="mp4",
    )


class TestPublishingPipeline(unittest.TestCase):
    def _create_fixture_files(self, tmp_dir: Path) -> tuple[Path, Path, Path]:
        video = tmp_dir / "chapter07.mp4"
        video.write_bytes(b"fake-video-content-007")
        thumb = tmp_dir / "thumb.jpg"
        Image.new("RGB", (1280, 720), color=(20, 40, 80)).save(thumb, format="JPEG")
        meta = tmp_dir / "chapter07.json"
        meta.write_text(
            json.dumps(
                {
                    "title": "SSS-Class Suicide Hunter - Chapter 7",
                    "description": "Recap",
                    "tags": ["manhwa"],
                    "type": "long",
                    "thumbnail": str(thumb),
                    "playlist_id": "PL_TEST_123",
                    "visibility": "private",
                }
            ),
            encoding="utf-8",
        )
        return video, meta, thumb

    def _make_config(self, tmp_dir: Path) -> AppConfig:
        return AppConfig(
            base_dir=tmp_dir,
            upload=UploadConfig(
                chunk_size_mb=1,
                max_retries=2,
                prevent_duplicates=True,
                file_ready_timeout_seconds=0.1,
                file_ready_poll_seconds=0.01,
            ),
            database=DatabaseConfig(path=str(tmp_dir / "publisher.db")),
            paths=PathsConfig(logs=str(tmp_dir / "logs"), credentials=str(tmp_dir / "creds")),
            safety=SafetyConfig(require_approval=True, allow_publication=True),
        )

    def test_full_publish_and_duplicate_prevention(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            video, meta, _ = self._create_fixture_files(tmp_dir)
            cfg = self._make_config(tmp_dir)
            repo = JobRepository(cfg.db_path)

            yt = MagicMock()
            yt.videos.return_value.insert.return_value.next_chunk.return_value = (
                None,
                {"id": "VID_FULL_01"},
            )
            yt.thumbnails.return_value.set.return_value.execute.return_value = {"items": []}
            yt.playlistItems.return_value.insert.return_value.execute.return_value = {"id": "PI1"}
            yt.videos.return_value.list.return_value.execute.return_value = {
                "items": [{"status": {"uploadStatus": "uploaded"}}]
            }

            pipeline = PublishingPipeline(cfg, repository=repo, youtube_service=yt)
            with patch("publisher.core.validator.probe_video", return_value=_fake_probe()):
                res1 = pipeline.publish(video_path=video, metadata_path=meta)
                self.assertTrue(res1.success)
                self.assertEqual(res1.exit_code, ExitCode.SUCCESS)
                self.assertEqual(res1.video_id, "VID_FULL_01")
                self.assertEqual(res1.status, "uploaded")

                # Second publish of identical video must be rejected as duplicate
                res2 = pipeline.publish(video_path=video, metadata_path=meta)
                self.assertFalse(res2.success)
                self.assertEqual(res2.exit_code, ExitCode.DUPLICATE_VIDEO)
                self.assertEqual(res2.video_id, "VID_FULL_01")

    def test_thumbnail_failure_and_retry_never_reuploads_video(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            video, meta, _ = self._create_fixture_files(tmp_dir)
            cfg = self._make_config(tmp_dir)
            repo = JobRepository(cfg.db_path)

            yt = MagicMock()
            yt.videos.return_value.insert.return_value.next_chunk.return_value = (
                None,
                {"id": "VID_KEEP_ME"},
            )
            yt.thumbnails.return_value.set.return_value.execute.side_effect = RuntimeError(
                "thumbnail API failure"
            )
            yt.playlistItems.return_value.insert.return_value.execute.return_value = {"id": "PI1"}
            yt.videos.return_value.list.return_value.execute.return_value = {
                "items": [{"status": {"uploadStatus": "uploaded"}}]
            }

            pipeline = PublishingPipeline(cfg, repository=repo, youtube_service=yt)
            with patch("publisher.core.validator.probe_video", return_value=_fake_probe()):
                first = pipeline.publish(video_path=video, metadata_path=meta)

            self.assertFalse(first.success)
            self.assertEqual(first.exit_code, ExitCode.UPLOAD_FAILURE)
            self.assertEqual(first.video_id, "VID_KEEP_ME")
            assert first.job_id is not None

            # Fix thumbnail call and retry job
            yt.thumbnails.return_value.set.return_value.execute.side_effect = None
            yt.thumbnails.return_value.set.return_value.execute.return_value = {"items": []}

            recovered = pipeline.retry_job(first.job_id)
            self.assertTrue(recovered.success)
            self.assertEqual(recovered.video_id, "VID_KEEP_ME")
            # Crucial invariant: videos().insert() was called ONLY ONCE across both runs!
            self.assertEqual(yt.videos.return_value.insert.call_count, 1)

            ops = repo.get_operations(first.job_id)
            self.assertEqual(ops[OperationType.VIDEO_UPLOAD].status, OperationStatus.COMPLETED)
            self.assertEqual(ops[OperationType.THUMBNAIL_UPLOAD].status, OperationStatus.COMPLETED)
            self.assertEqual(ops[OperationType.PLAYLIST_INSERT].status, OperationStatus.COMPLETED)

    def test_playlist_failure_and_retry_skips_video_and_thumbnail(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            video, meta, _ = self._create_fixture_files(tmp_dir)
            cfg = self._make_config(tmp_dir)
            repo = JobRepository(cfg.db_path)

            yt = MagicMock()
            yt.videos.return_value.insert.return_value.next_chunk.return_value = (
                None,
                {"id": "VID_PL_01"},
            )
            yt.thumbnails.return_value.set.return_value.execute.return_value = {"items": []}
            yt.playlistItems.return_value.insert.return_value.execute.side_effect = RuntimeError(
                "playlist error"
            )
            yt.videos.return_value.list.return_value.execute.return_value = {
                "items": [{"status": {"uploadStatus": "uploaded"}}]
            }

            pipeline = PublishingPipeline(cfg, repository=repo, youtube_service=yt)
            with patch("publisher.core.validator.probe_video", return_value=_fake_probe()):
                first = pipeline.publish(video_path=video, metadata_path=meta)

            self.assertFalse(first.success)
            assert first.job_id is not None

            # Fix playlist and retry
            yt.playlistItems.return_value.insert.return_value.execute.side_effect = None
            yt.playlistItems.return_value.insert.return_value.execute.return_value = {"id": "PI2"}

            recovered = pipeline.retry_job(first.job_id)
            self.assertTrue(recovered.success)
            self.assertEqual(yt.videos.return_value.insert.call_count, 1)
            self.assertEqual(yt.thumbnails.return_value.set.call_count, 1)
            self.assertEqual(yt.playlistItems.return_value.insert.call_count, 2)

    def test_uncertain_timeout_marks_needs_attention_and_blocks_blind_retry(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            video, meta, _ = self._create_fixture_files(tmp_dir)
            cfg = self._make_config(tmp_dir)
            repo = JobRepository(cfg.db_path)

            yt = MagicMock()
            yt.videos.return_value.insert.return_value.next_chunk.side_effect = TimeoutError(
                "socket timed out"
            )

            pipeline = PublishingPipeline(cfg, repository=repo, youtube_service=yt)
            with patch("publisher.core.validator.probe_video", return_value=_fake_probe()):
                res = pipeline.publish(video_path=video, metadata_path=meta)

            self.assertFalse(res.success)
            self.assertEqual(res.status, JobStatus.NEEDS_ATTENTION.value)
            assert res.job_id is not None

            retry_res = pipeline.retry_job(res.job_id)
            self.assertFalse(retry_res.success)
            self.assertIn("manual reconciliation", retry_res.message.lower())
            self.assertEqual(yt.videos.return_value.insert.call_count, 1)

    def test_short_linked_to_long_video_via_related_job_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            long_video, long_meta, _ = self._create_fixture_files(tmp_dir)
            short_video = tmp_dir / "chapter07_short.mp4"
            short_video.write_bytes(b"fake-short-video-content-007")
            short_meta = tmp_dir / "chapter07_short.json"
            short_meta.write_text(
                json.dumps(
                    {
                        "title": "Chapter 7 Short #shorts",
                        "description": "Best moment!",
                        "type": "short",
                        "visibility": "private",
                    }
                ),
                encoding="utf-8",
            )

            cfg = self._make_config(tmp_dir)
            repo = JobRepository(cfg.db_path)

            yt = MagicMock()
            yt.videos.return_value.insert.return_value.next_chunk.side_effect = [
                (None, {"id": "LONG_VID_007"}),
                (None, {"id": "SHORT_VID_007"}),
            ]
            yt.thumbnails.return_value.set.return_value.execute.return_value = {"items": []}
            yt.playlistItems.return_value.insert.return_value.execute.return_value = {"id": "PI1"}
            yt.videos.return_value.list.return_value.execute.return_value = {
                "items": [{"status": {"uploadStatus": "uploaded"}}]
            }

            pipeline = PublishingPipeline(cfg, repository=repo, youtube_service=yt)
            with patch("publisher.core.validator.probe_video", return_value=_fake_probe()):
                long_res = pipeline.publish(video_path=long_video, metadata_path=long_meta)
                self.assertTrue(long_res.success)
                assert long_res.job_id is not None

                short_res = pipeline.publish(
                    video_path=short_video,
                    metadata_path=short_meta,
                    related_job_id=long_res.job_id,
                )

            self.assertTrue(short_res.success)
            self.assertEqual(short_res.video_id, "SHORT_VID_007")
            self.assertEqual(short_res.related_video_id, "LONG_VID_007")
            self.assertEqual(
                short_res.related_video_url, "https://www.youtube.com/watch?v=LONG_VID_007"
            )
            self.assertEqual(
                short_res.studio_edit_url,
                "https://studio.youtube.com/video/SHORT_VID_007/edit",
            )

            # Verify description passed to YouTube included the full video link
            second_insert_kwargs = yt.videos.return_value.insert.call_args_list[1].kwargs
            sent_desc = second_insert_kwargs["body"]["snippet"]["description"]
            self.assertIn("https://www.youtube.com/watch?v=LONG_VID_007", sent_desc)

            # Verify persisted in SQLite
            assert short_res.job_id is not None
            saved_short = repo.get_job(short_res.job_id)
            assert saved_short is not None
            self.assertEqual(saved_short.related_video_id, "LONG_VID_007")
            self.assertEqual(saved_short.related_job_id, long_res.job_id)


if __name__ == "__main__":
    unittest.main()
