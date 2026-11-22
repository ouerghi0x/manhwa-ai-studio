"""Transactional SQLite repository for upload jobs and operation states."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from publisher.database.migrations import run_migrations
from publisher.database.models import (
    JobOperation,
    JobStatus,
    OperationStatus,
    OperationType,
    UploadJob,
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class DuplicateJobError(Exception):
    """Raised when attempting to insert a job with an already-tracked SHA-256 hash."""

    def __init__(self, message: str, existing_job: UploadJob) -> None:
        super().__init__(message)
        self.existing_job = existing_job


class JobRepository:
    """SQLite-backed repository for upload jobs and their sub-operations."""

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            run_migrations(conn)

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(str(self.db_path), timeout=30.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("PRAGMA journal_mode = WAL;")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    @staticmethod
    def _row_to_job(row: sqlite3.Row) -> UploadJob:
        return UploadJob(
            id=int(row["id"]),
            video_path=str(row["video_path"]),
            metadata_path=str(row["metadata_path"]),
            sha256_hash=str(row["sha256_hash"]),
            youtube_video_id=row["youtube_video_id"],
            video_url=row["video_url"],
            status=JobStatus(row["status"]),
            publish_at=row["publish_at"],
            upload_progress=float(row["upload_progress"]),
            resumable_uri=row["resumable_uri"],
            title=row["title"],
            video_type=row["video_type"],
            visibility=row["visibility"],
            thumbnail_path=row["thumbnail_path"],
            playlist_id=row["playlist_id"],
            created_at=str(row["created_at"]),
            updated_at=str(row["updated_at"]),
            error_details=row["error_details"],
            related_video_id=row["related_video_id"],
            related_job_id=int(row["related_job_id"]) if row["related_job_id"] is not None else None,
        )

    @staticmethod
    def _row_to_operation(row: sqlite3.Row) -> JobOperation:
        return JobOperation(
            id=int(row["id"]),
            job_id=int(row["job_id"]),
            operation_type=OperationType(row["operation_type"]),
            status=OperationStatus(row["status"]),
            attempts=int(row["attempts"]),
            last_error=row["last_error"],
            created_at=str(row["created_at"]),
            updated_at=str(row["updated_at"]),
        )

    def create_job(
        self,
        *,
        video_path: str,
        metadata_path: str,
        sha256_hash: str,
        title: str | None = None,
        video_type: str | None = None,
        visibility: str | None = None,
        publish_at: str | None = None,
        thumbnail_path: str | None = None,
        playlist_id: str | None = None,
        related_video_id: str | None = None,
        related_job_id: int | None = None,
        status: JobStatus = JobStatus.PENDING,
    ) -> UploadJob:
        """Create a new upload job and initialize its four tracked operations."""
        now = _utc_now()
        try:
            with self._connect() as conn:
                cursor = conn.execute(
                    """
                    INSERT INTO upload_jobs (
                        video_path, metadata_path, sha256_hash, status,
                        publish_at, upload_progress, title, video_type,
                        visibility, thumbnail_path, playlist_id,
                        related_video_id, related_job_id,
                        created_at, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, 0.0, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                    """,
                    (
                        video_path,
                        metadata_path,
                        sha256_hash,
                        status.value,
                        publish_at,
                        title,
                        video_type,
                        visibility,
                        thumbnail_path,
                        playlist_id,
                        related_video_id,
                        related_job_id,
                        now,
                        now,
                    ),
                )
                job_id = int(cursor.lastrowid)  # type: ignore[arg-type]

                for op_type in OperationType:
                    op_status = OperationStatus.PENDING
                    if op_type == OperationType.THUMBNAIL_UPLOAD and not thumbnail_path:
                        op_status = OperationStatus.SKIPPED
                    elif op_type == OperationType.PLAYLIST_INSERT and not playlist_id:
                        op_status = OperationStatus.SKIPPED
                    conn.execute(
                        """
                        INSERT INTO job_operations (
                            job_id, operation_type, status, attempts,
                            last_error, created_at, updated_at
                        )
                        VALUES (?, ?, ?, 0, NULL, ?, ?);
                        """,
                        (job_id, op_type.value, op_status.value, now, now),
                    )
        except sqlite3.IntegrityError as exc:
            existing = self.get_job_by_hash(sha256_hash)
            if existing is not None:
                raise DuplicateJobError(
                    f"Video with SHA-256 {sha256_hash} already exists as job #{existing.id}.",
                    existing,
                ) from exc
            raise

        created = self.get_job(job_id)
        assert created is not None
        return created

    def get_job(self, job_id: int) -> UploadJob | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM upload_jobs WHERE id = ?;", (job_id,)).fetchone()
            return self._row_to_job(row) if row else None

    def get_job_by_hash(self, sha256_hash: str) -> UploadJob | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM upload_jobs WHERE sha256_hash = ?;", (sha256_hash,)
            ).fetchone()
            return self._row_to_job(row) if row else None

    def get_job_by_video_id(self, youtube_video_id: str) -> UploadJob | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM upload_jobs WHERE youtube_video_id = ?;", (youtube_video_id,)
            ).fetchone()
            return self._row_to_job(row) if row else None

    def list_jobs(
        self,
        *,
        statuses: list[JobStatus] | None = None,
        limit: int = 50,
    ) -> list[UploadJob]:
        with self._connect() as conn:
            if statuses:
                placeholders = ",".join("?" for _ in statuses)
                rows = conn.execute(
                    f"SELECT * FROM upload_jobs WHERE status IN ({placeholders}) "
                    "ORDER BY id DESC LIMIT ?;",
                    (*[s.value for s in statuses], limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM upload_jobs ORDER BY id DESC LIMIT ?;", (limit,)
                ).fetchall()
            return [self._row_to_job(row) for row in rows]

    def list_pending_queue(self, limit: int = 50) -> list[UploadJob]:
        return self.list_jobs(
            statuses=[
                JobStatus.PENDING,
                JobStatus.VALIDATING,
                JobStatus.UPLOADING,
                JobStatus.UPLOADED,
                JobStatus.PROCESSING,
                JobStatus.FAILED,
                JobStatus.NEEDS_ATTENTION,
            ],
            limit=limit,
        )

    def update_job_status(
        self,
        job_id: int,
        status: JobStatus,
        *,
        error_details: str | None = None,
        upload_progress: float | None = None,
    ) -> None:
        now = _utc_now()
        with self._connect() as conn:
            if upload_progress is not None:
                conn.execute(
                    """
                    UPDATE upload_jobs
                    SET status = ?, error_details = ?, upload_progress = ?, updated_at = ?
                    WHERE id = ?;
                    """,
                    (status.value, error_details, float(upload_progress), now, job_id),
                )
            else:
                conn.execute(
                    """
                    UPDATE upload_jobs
                    SET status = ?, error_details = ?, updated_at = ?
                    WHERE id = ?;
                    """,
                    (status.value, error_details, now, job_id),
                )

    def update_upload_progress(self, job_id: int, progress: float) -> None:
        now = _utc_now()
        clamped = max(0.0, min(100.0, float(progress)))
        with self._connect() as conn:
            conn.execute(
                "UPDATE upload_jobs SET upload_progress = ?, updated_at = ? WHERE id = ?;",
                (clamped, now, job_id),
            )

    def save_resumable_uri(self, job_id: int, resumable_uri: str | None) -> None:
        now = _utc_now()
        with self._connect() as conn:
            conn.execute(
                "UPDATE upload_jobs SET resumable_uri = ?, updated_at = ? WHERE id = ?;",
                (resumable_uri, now, job_id),
            )

    def record_youtube_video_id(self, job_id: int, video_id: str) -> None:
        """Persist the YouTube video ID immediately upon acceptance to prevent duplicates."""
        now = _utc_now()
        url = f"https://www.youtube.com/watch?v={video_id}"
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE upload_jobs
                SET youtube_video_id = ?, video_url = ?, upload_progress = 100.0,
                    resumable_uri = NULL, updated_at = ?
                WHERE id = ?;
                """,
                (video_id, url, now, job_id),
            )

    def get_operations(self, job_id: int) -> dict[OperationType, JobOperation]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM job_operations WHERE job_id = ? ORDER BY id ASC;",
                (job_id,),
            ).fetchall()
            return {
                OperationType(row["operation_type"]): self._row_to_operation(row)
                for row in rows
            }

    def update_operation(
        self,
        job_id: int,
        operation_type: OperationType,
        status: OperationStatus,
        *,
        increment_attempts: bool = False,
        last_error: str | None = None,
    ) -> None:
        now = _utc_now()
        with self._connect() as conn:
            if increment_attempts:
                conn.execute(
                    """
                    UPDATE job_operations
                    SET status = ?, attempts = attempts + 1, last_error = ?, updated_at = ?
                    WHERE job_id = ? AND operation_type = ?;
                    """,
                    (status.value, last_error, now, job_id, operation_type.value),
                )
            else:
                conn.execute(
                    """
                    UPDATE job_operations
                    SET status = ?, last_error = ?, updated_at = ?
                    WHERE job_id = ? AND operation_type = ?;
                    """,
                    (status.value, last_error, now, job_id, operation_type.value),
                )
