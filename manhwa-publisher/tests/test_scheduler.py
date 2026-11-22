"""Unit tests for scheduling rules and publication approval safety policy."""

from __future__ import annotations

import unittest
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from publisher.config import SafetyConfig
from publisher.core.metadata import VideoMetadata
from publisher.core.scheduler import (
    ApprovalRequiredError,
    SchedulingError,
    resolve_publication_plan,
)


class TestScheduler(unittest.TestCase):
    def setUp(self) -> None:
        self.tz = ZoneInfo("Africa/Tunis")
        self.now = datetime(2026, 11, 19, 12, 0, 0, tzinfo=timezone.utc)

    def test_scheduled_video_sets_private_and_utc_publish_at(self) -> None:
        meta = VideoMetadata(
            title="Episode 1",
            video_type="long",
            publish_at=datetime(2026, 11, 20, 20, 0, 0, tzinfo=self.tz),
        )
        plan = resolve_publication_plan(
            meta,
            safety=SafetyConfig(require_approval=False, allow_publication=True),
            tz=self.tz,
            now_utc=self.now,
        )
        self.assertEqual(plan.privacy_status, "private")
        self.assertEqual(plan.publish_at_utc, "2026-11-20T19:00:00Z")
        self.assertTrue(plan.is_scheduled)
        self.assertEqual(plan.final_job_status, "scheduled")

    def test_past_publish_at_raises_scheduling_error(self) -> None:
        meta = VideoMetadata(
            title="Episode 1",
            video_type="long",
            publish_at=datetime(2026, 11, 18, 10, 0, 0, tzinfo=self.tz),
        )
        with self.assertRaises(SchedulingError):
            resolve_publication_plan(
                meta,
                safety=SafetyConfig(require_approval=False, allow_publication=True),
                tz=self.tz,
                now_utc=self.now,
            )

    def test_require_approval_blocks_public_without_approve_flag(self) -> None:
        meta = VideoMetadata(title="Episode 1", video_type="long", visibility="public")
        with self.assertRaises(ApprovalRequiredError):
            resolve_publication_plan(
                meta,
                safety=SafetyConfig(require_approval=True, allow_publication=True),
                tz=self.tz,
                approve=False,
                now_utc=self.now,
            )

    def test_private_upload_allowed_even_when_require_approval_true(self) -> None:
        meta = VideoMetadata(
            title="Episode 1",
            video_type="long",
            publish_at=datetime(2026, 11, 20, 20, 0, 0, tzinfo=self.tz),
        )
        plan = resolve_publication_plan(
            meta,
            safety=SafetyConfig(require_approval=True, allow_publication=True),
            tz=self.tz,
            visibility_override="private",
            approve=False,
            now_utc=self.now,
        )
        self.assertEqual(plan.privacy_status, "private")
        self.assertIsNone(plan.publish_at_utc)
        self.assertEqual(plan.final_job_status, "uploaded")

    def test_publish_now_with_approve(self) -> None:
        meta = VideoMetadata(title="Episode 1", video_type="long")
        plan = resolve_publication_plan(
            meta,
            safety=SafetyConfig(require_approval=True, allow_publication=True),
            tz=self.tz,
            publish_now=True,
            approve=True,
            now_utc=self.now,
        )
        self.assertEqual(plan.privacy_status, "public")
        self.assertIsNone(plan.publish_at_utc)
        self.assertEqual(plan.final_job_status, "published")


if __name__ == "__main__":
    unittest.main()
