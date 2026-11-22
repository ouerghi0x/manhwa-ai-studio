"""Unit tests for SQLite persistence, migrations, duplicate prevention, and operations."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from publisher.database.models import JobStatus, OperationStatus, OperationType
from publisher.database.repository import DuplicateJobError, JobRepository


class TestDatabaseRepository(unittest.TestCase):
    def test_create_job_and_operations(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = JobRepository(Path(tmp) / "publisher.db")
            job = repo.create_job(
                video_path="v.mp4",
                metadata_path="v.json",
                sha256_hash="abc123",
                title="Chapter 1",
                video_type="long",
                visibility="private",
                thumbnail_path="t.jpg",
                playlist_id="PL1",
            )
            self.assertEqual(job.id, 1)
            self.assertEqual(job.status, JobStatus.PENDING)

            ops = repo.get_operations(job.id)
            self.assertEqual(len(ops), 4)
            self.assertEqual(ops[OperationType.VIDEO_UPLOAD].status, OperationStatus.PENDING)
            self.assertEqual(ops[OperationType.THUMBNAIL_UPLOAD].status, OperationStatus.PENDING)
            self.assertEqual(ops[OperationType.PLAYLIST_INSERT].status, OperationStatus.PENDING)

    def test_duplicate_sha256_raises_duplicate_job_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = JobRepository(Path(tmp) / "publisher.db")
            first = repo.create_job(
                video_path="v1.mp4", metadata_path="v1.json", sha256_hash="same_hash"
            )
            with self.assertRaises(DuplicateJobError) as ctx:
                repo.create_job(
                    video_path="v2.mp4", metadata_path="v2.json", sha256_hash="same_hash"
                )
            self.assertEqual(ctx.exception.existing_job.id, first.id)

    def test_record_video_id_and_lookup(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = JobRepository(Path(tmp) / "publisher.db")
            job = repo.create_job(
                video_path="v.mp4", metadata_path="v.json", sha256_hash="hash_xyz"
            )
            repo.save_resumable_uri(job.id, "https://upload.example/session/123")
            self.assertEqual(
                repo.get_job(job.id).resumable_uri,  # type: ignore[union-attr]
                "https://upload.example/session/123",
            )

            repo.record_youtube_video_id(job.id, "YT_VID_999")
            found = repo.get_job_by_video_id("YT_VID_999")
            self.assertIsNotNone(found)
            assert found is not None
            self.assertEqual(found.video_url, "https://www.youtube.com/watch?v=YT_VID_999")
            self.assertIsNone(found.resumable_uri)
            self.assertEqual(found.upload_progress, 100.0)


if __name__ == "__main__":
    unittest.main()
