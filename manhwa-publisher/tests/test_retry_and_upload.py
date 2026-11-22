"""Unit tests for retry classification, backoff, and resumable upload recovery."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from googleapiclient.errors import HttpError
import httplib2

from publisher.core.metadata import VideoMetadata
from publisher.core.retry import ErrorCategory, classify_exception, execute_with_retry
from publisher.core.scheduler import PublicationPlan
from publisher.youtube.uploader import (
    UncertainUploadError,
    UploadError,
    upload_video_resumable,
)


def _make_http_error(status: int, body: bytes = b"error") -> HttpError:
    resp = httplib2.Response({"status": str(status)})
    return HttpError(resp, body)


class TestRetryAndUpload(unittest.TestCase):
    def test_classify_http_errors(self) -> None:
        self.assertEqual(classify_exception(_make_http_error(503)), ErrorCategory.RETRYABLE)
        self.assertEqual(classify_exception(_make_http_error(429)), ErrorCategory.RETRYABLE)
        self.assertEqual(classify_exception(_make_http_error(401)), ErrorCategory.AUTH)
        self.assertEqual(
            classify_exception(_make_http_error(403, b"quotaExceeded")),
            ErrorCategory.QUOTA_EXCEEDED,
        )
        self.assertEqual(classify_exception(_make_http_error(400)), ErrorCategory.NON_RETRYABLE)
        self.assertEqual(classify_exception(TimeoutError("timed out")), ErrorCategory.UNCERTAIN_TIMEOUT)

    def test_execute_with_retry_succeeds_after_transient_503(self) -> None:
        calls = {"n": 0}

        def flaky() -> str:
            calls["n"] += 1
            if calls["n"] < 3:
                raise _make_http_error(503)
            return "ok"

        result = execute_with_retry(
            flaky, operation_name="test", max_retries=4, sleep_fn=lambda _: None
        )
        self.assertEqual(result, "ok")
        self.assertEqual(calls["n"], 3)

    def test_resumable_upload_recovers_from_chunk_error_and_saves_uri(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vid = Path(tmp) / "ep.mp4"
            vid.write_bytes(b"video bytes")

            status1 = MagicMock()
            status1.progress.return_value = 0.5

            req = MagicMock()
            req.resumable_uri = "https://upload.youtube.example/session/abc"
            req.next_chunk.side_effect = [
                (status1, None),
                _make_http_error(503),
                (None, {"id": "YT_OK_123"}),
            ]
            yt = MagicMock()
            yt.videos.return_value.insert.return_value = req

            progress_seen: list[float] = []
            uris_seen: list[str] = []
            meta = VideoMetadata(title="Test", video_type="long")
            plan = PublicationPlan(
                privacy_status="private",
                publish_at_utc=None,
                is_scheduled=False,
                final_job_status="uploaded",
            )

            video_id = upload_video_resumable(
                yt,
                vid,
                meta,
                plan,
                max_retries=3,
                on_progress=progress_seen.append,
                on_resumable_uri=uris_seen.append,
                sleep_fn=lambda _: None,
            )
            self.assertEqual(video_id, "YT_OK_123")
            self.assertIn(50.0, progress_seen)
            self.assertIn(100.0, progress_seen)
            self.assertIn("https://upload.youtube.example/session/abc", uris_seen)

    def test_uncertain_timeout_raises_uncertain_upload_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vid = Path(tmp) / "ep.mp4"
            vid.write_bytes(b"video bytes")

            req = MagicMock()
            req.next_chunk.side_effect = TimeoutError("read timed out")
            yt = MagicMock()
            yt.videos.return_value.insert.return_value = req

            meta = VideoMetadata(title="Test", video_type="long")
            plan = PublicationPlan(
                privacy_status="private",
                publish_at_utc=None,
                is_scheduled=False,
                final_job_status="uploaded",
            )
            with self.assertRaises(UncertainUploadError):
                upload_video_resumable(yt, vid, meta, plan, sleep_fn=lambda _: None)

    def test_non_retryable_400_raises_upload_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vid = Path(tmp) / "ep.mp4"
            vid.write_bytes(b"video bytes")

            req = MagicMock()
            req.next_chunk.side_effect = _make_http_error(400)
            yt = MagicMock()
            yt.videos.return_value.insert.return_value = req

            meta = VideoMetadata(title="Test", video_type="long")
            plan = PublicationPlan(
                privacy_status="private",
                publish_at_utc=None,
                is_scheduled=False,
                final_job_status="uploaded",
            )
            with self.assertRaises(UploadError):
                upload_video_resumable(yt, vid, meta, plan, sleep_fn=lambda _: None)


if __name__ == "__main__":
    unittest.main()
