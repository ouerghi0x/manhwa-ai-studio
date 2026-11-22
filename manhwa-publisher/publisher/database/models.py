"""Data models and status enums for SQLite persistence."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class JobStatus(str, Enum):
    """Lifecycle states of an upload job."""

    PENDING = "pending"
    VALIDATING = "validating"
    UPLOADING = "uploading"
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    SCHEDULED = "scheduled"
    PUBLISHED = "published"
    FAILED = "failed"
    NEEDS_ATTENTION = "needs_attention"


class OperationType(str, Enum):
    """Independent publishing operations tracked per job."""

    VIDEO_UPLOAD = "video_upload"
    THUMBNAIL_UPLOAD = "thumbnail_upload"
    PLAYLIST_INSERT = "playlist_insert"
    PROCESSING_VERIFICATION = "processing_verification"


class OperationStatus(str, Enum):
    """States of an individual publishing operation."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    NEEDS_ATTENTION = "needs_attention"


@dataclass
class UploadJob:
    """Persistent record of a single video upload job."""

    id: int
    video_path: str
    metadata_path: str
    sha256_hash: str
    youtube_video_id: str | None
    video_url: str | None
    status: JobStatus
    publish_at: str | None
    upload_progress: float
    resumable_uri: str | None
    title: str | None
    video_type: str | None
    visibility: str | None
    thumbnail_path: str | None
    playlist_id: str | None
    created_at: str
    updated_at: str
    error_details: str | None
    related_video_id: str | None = None
    related_job_id: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "job_id": self.id,
            "video_path": self.video_path,
            "metadata_path": self.metadata_path,
            "sha256_hash": self.sha256_hash,
            "video_id": self.youtube_video_id,
            "url": self.video_url,
            "status": self.status.value,
            "publish_at": self.publish_at,
            "upload_progress": self.upload_progress,
            "title": self.title,
            "video_type": self.video_type,
            "visibility": self.visibility,
            "thumbnail_path": self.thumbnail_path,
            "playlist_id": self.playlist_id,
            "related_video_id": self.related_video_id,
            "related_job_id": self.related_job_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "error_details": self.error_details,
        }


@dataclass
class JobOperation:
    """Persistent record of an independent operation belonging to an upload job."""

    id: int
    job_id: int
    operation_type: OperationType
    status: OperationStatus
    attempts: int
    last_error: str | None
    created_at: str
    updated_at: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "job_id": self.job_id,
            "operation_type": self.operation_type.value,
            "status": self.status.value,
            "attempts": self.attempts,
            "last_error": self.last_error,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
