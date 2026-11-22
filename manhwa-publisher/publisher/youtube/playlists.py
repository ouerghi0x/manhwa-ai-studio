"""YouTube playlist management via playlistItems.insert."""

from __future__ import annotations

import logging
from typing import Any

from publisher.core.retry import execute_with_retry

logger = logging.getLogger("publisher.youtube.playlists")


def add_video_to_playlist(
    youtube_service: Any,
    video_id: str,
    playlist_id: str,
    *,
    max_retries: int = 5,
) -> dict[str, Any]:
    """Add an uploaded video to a target YouTube playlist."""
    body = {
        "snippet": {
            "playlistId": playlist_id,
            "resourceId": {
                "kind": "youtube#video",
                "videoId": video_id,
            },
        }
    }

    def _call() -> dict[str, Any]:
        result: dict[str, Any] = (
            youtube_service.playlistItems()
            .insert(part="snippet", body=body)
            .execute()
        )
        return result

    response = execute_with_retry(
        _call,
        operation_name=f"playlistItems.insert({playlist_id}, {video_id})",
        max_retries=max_retries,
        allow_timeout_retry=True,
    )
    logger.info("Video %s added to playlist %s.", video_id, playlist_id)
    return response
