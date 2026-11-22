"""YouTube custom thumbnail upload via thumbnails.set."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from googleapiclient.http import MediaFileUpload

from publisher.core.retry import execute_with_retry

logger = logging.getLogger("publisher.youtube.thumbnails")


def set_video_thumbnail(
    youtube_service: Any,
    video_id: str,
    thumbnail_path: Path,
    *,
    max_retries: int = 5,
) -> dict[str, Any]:
    """Upload and attach a custom thumbnail to an existing YouTube video."""
    media = MediaFileUpload(str(thumbnail_path), resumable=False)

    def _call() -> dict[str, Any]:
        result: dict[str, Any] = (
            youtube_service.thumbnails()
            .set(videoId=video_id, media_body=media)
            .execute()
        )
        return result

    try:
        response = execute_with_retry(
            _call,
            operation_name=f"thumbnails.set({video_id})",
            max_retries=max_retries,
            allow_timeout_retry=True,
        )
    finally:
        stream = media.stream()
        if stream is not None and not stream.closed:
            stream.close()
    logger.info("Thumbnail uploaded for video %s.", video_id)
    return response
