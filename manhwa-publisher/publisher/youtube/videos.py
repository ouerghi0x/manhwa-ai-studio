"""YouTube video status inspection and channel health checks."""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from typing import Any

from publisher.core.retry import execute_with_retry

logger = logging.getLogger("publisher.youtube.videos")


def get_video_details(
    youtube_service: Any,
    video_id: str,
    *,
    max_retries: int = 3,
) -> dict[str, Any] | None:
    """Retrieve snippet, status, and processingDetails for a YouTube video."""

    def _call() -> dict[str, Any]:
        result: dict[str, Any] = (
            youtube_service.videos()
            .list(part="snippet,status,processingDetails", id=video_id)
            .execute()
        )
        return result

    response = execute_with_retry(
        _call,
        operation_name=f"videos.list({video_id})",
        max_retries=max_retries,
    )
    items = response.get("items") or []
    if not items:
        return None
    item: dict[str, Any] = items[0]
    return item


def wait_for_processing(
    youtube_service: Any,
    video_id: str,
    *,
    timeout_seconds: float = 600.0,
    poll_interval_seconds: float = 15.0,
    sleep_fn: Callable[[float], None] = time.sleep,
) -> dict[str, Any]:
    """Poll videos.list until YouTube finishes processing the video or times out."""
    deadline = time.monotonic() + timeout_seconds
    last_details: dict[str, Any] = {}

    while True:
        details = get_video_details(youtube_service, video_id)
        if details is not None:
            last_details = details
            proc_status = (details.get("processingDetails") or {}).get("processingStatus")
            upload_status = (details.get("status") or {}).get("uploadStatus")
            logger.info(
                "YouTube status for %s: uploadStatus=%s, processingStatus=%s",
                video_id,
                upload_status,
                proc_status,
            )
            if proc_status in {"succeeded", "failed", "terminated"} or upload_status in {
                "processed",
                "failed",
                "rejected",
            }:
                return details

        if time.monotonic() >= deadline:
            return last_details

        sleep_fn(min(poll_interval_seconds, max(0.1, deadline - time.monotonic())))


def get_authenticated_channel(youtube_service: Any) -> dict[str, Any] | None:
    """Fetch the authenticated user's channel info for doctor/health checks."""
    response: dict[str, Any] = (
        youtube_service.channels()
        .list(part="snippet,statistics", mine=True)
        .execute()
    )
    items = response.get("items") or []
    if not items:
        return None
    channel: dict[str, Any] = items[0]
    return channel
