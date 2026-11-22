"""Resumable chunked video uploader for YouTube Data API v3."""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from googleapiclient.http import MediaFileUpload

from publisher.core.metadata import VideoMetadata
from publisher.core.retry import ErrorCategory, classify_exception, compute_backoff_seconds
from publisher.core.scheduler import PublicationPlan

logger = logging.getLogger("publisher.youtube.uploader")


class UploadError(Exception):
    """Raised when a video upload fails permanently or exhausts retries."""


class UncertainUploadError(UploadError):
    """Raised when a network timeout occurs and YouTube's acceptance state is unknown.

    Callers MUST NOT blindly retry videos.insert after this error without reconciling.
    """


def build_video_insert_body(
    metadata: VideoMetadata,
    plan: PublicationPlan,
) -> dict[str, Any]:
    """Construct the YouTube Data API v3 videos.insert request body."""
    snippet: dict[str, Any] = {
        "title": metadata.title,
        "description": metadata.description,
        "categoryId": metadata.category_id,
        "defaultLanguage": metadata.language,
        "defaultAudioLanguage": metadata.language,
    }
    if metadata.tags:
        snippet["tags"] = list(metadata.tags)

    status: dict[str, Any] = {
        "privacyStatus": plan.privacy_status,
        "selfDeclaredMadeForKids": False,
    }
    if plan.publish_at_utc:
        status["publishAt"] = plan.publish_at_utc

    return {
        "snippet": snippet,
        "status": status,
    }


def upload_video_resumable(
    youtube_service: Any,
    video_path: Path,
    metadata: VideoMetadata,
    plan: PublicationPlan,
    *,
    chunk_size_bytes: int = 8 * 1024 * 1024,
    max_retries: int = 8,
    resumable_uri: str | None = None,
    on_progress: Callable[[float], None] | None = None,
    on_resumable_uri: Callable[[str], None] | None = None,
    sleep_fn: Callable[[float], None] = time.sleep,
) -> str:
    """Upload a video using YouTube's resumable upload protocol.

    Returns the YouTube video ID upon confirmed API acceptance.
    """
    body = build_video_insert_body(metadata, plan)
    media = MediaFileUpload(
        str(video_path),
        mimetype="video/*",
        chunksize=chunk_size_bytes,
        resumable=True,
    )
    try:
        request = youtube_service.videos().insert(
            part="snippet,status",
            body=body,
            media_body=media,
        )

        if resumable_uri:
            logger.info("Resuming previous YouTube upload session...")
            request.resumable_uri = resumable_uri

        response: dict[str, Any] | None = None
        retry_count = 0
        last_reported_pct = -1

        while response is None:
            try:
                status, response = request.next_chunk()

                # Persist resumable URI as soon as Google assigns one
                current_uri = getattr(request, "resumable_uri", None)
                if current_uri and on_resumable_uri is not None:
                    on_resumable_uri(str(current_uri))

                if status is not None:
                    pct = round(float(status.progress()) * 100.0, 2)
                    int_pct = int(pct)
                    if int_pct != last_reported_pct:
                        last_reported_pct = int_pct
                        logger.info("Upload progress: %d%%", int_pct)
                        if on_progress is not None:
                            on_progress(pct)
                retry_count = 0

            except Exception as exc:
                category = classify_exception(exc)

                if category == ErrorCategory.UNCERTAIN_TIMEOUT:
                    # Never blindly retry videos.insert after an uncertain timeout
                    raise UncertainUploadError(
                        f"Uncertain network timeout during video upload: {exc}. "
                        "Reconciliation or manual verification required to avoid duplicate uploads."
                    ) from exc

                if category != ErrorCategory.RETRYABLE:
                    raise UploadError(
                        f"Non-retryable error during video upload ({category.value}): {exc}"
                    ) from exc

                retry_count += 1
                if retry_count > max_retries:
                    raise UploadError(
                        f"Video upload failed after {max_retries} retries: {exc}"
                    ) from exc

                delay = compute_backoff_seconds(retry_count)
                logger.warning(
                    "Upload chunk interrupted (%s). Retrying %d/%d in %.2fs...",
                    exc,
                    retry_count,
                    max_retries,
                    delay,
                )
                sleep_fn(delay)
    finally:
        stream = media.stream()
        if stream is not None and not stream.closed:
            stream.close()

    video_id = response.get("id") if isinstance(response, dict) else None
    if not video_id or not isinstance(video_id, str):
        raise UploadError(f"YouTube API did not return a valid video ID: {response!r}")

    if on_progress is not None:
        on_progress(100.0)
    logger.info("Upload completed. YouTube Video ID: %s", video_id)
    return video_id
