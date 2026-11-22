"""End-to-end YouTube publishing pipeline with independent operation recovery."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any

from publisher.config import AppConfig
from publisher.core.metadata import MetadataValidationError, VideoMetadata, load_metadata
from publisher.core.scheduler import (
    ApprovalRequiredError,
    PublicationPlan,
    SchedulingError,
    resolve_publication_plan,
)
from publisher.core.validator import validate_video
from publisher.database.models import (
    JobStatus,
    OperationStatus,
    OperationType,
    UploadJob,
)
from publisher.database.repository import DuplicateJobError, JobRepository
from publisher.exit_codes import ExitCode
from publisher.utils.file_ready import wait_for_file_ready
from publisher.utils.hashing import compute_sha256
from publisher.youtube.auth import (
    AuthenticationError,
    build_youtube_service,
    get_valid_credentials,
)
from publisher.youtube.playlists import add_video_to_playlist
from publisher.youtube.thumbnails import set_video_thumbnail
from publisher.youtube.uploader import (
    UncertainUploadError,
    UploadError,
    upload_video_resumable,
)
from publisher.youtube.videos import get_video_details, wait_for_processing

logger = logging.getLogger("publisher.pipeline")


@dataclass
class PublishResult:
    """Structured outcome of a publish or retry pipeline run."""

    success: bool
    exit_code: ExitCode
    message: str
    job_id: int | None = None
    video_id: str | None = None
    url: str | None = None
    status: str | None = None
    related_video_id: str | None = None
    related_video_url: str | None = None
    studio_edit_url: str | None = None
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "success": self.success,
            "job_id": self.job_id,
            "video_id": self.video_id,
            "url": self.url,
            "status": self.status,
            "message": self.message,
        }
        if self.related_video_id:
            payload["related_video_id"] = self.related_video_id
            payload["related_video_url"] = self.related_video_url
        if self.studio_edit_url:
            payload["studio_edit_url"] = self.studio_edit_url
        if self.warnings:
            payload["warnings"] = list(self.warnings)
        if self.errors:
            payload["errors"] = list(self.errors)
        return payload


class PublishingPipeline:
    """Coordinates validation, deduplication, YouTube upload, thumbnail, playlist, and state."""

    def __init__(
        self,
        config: AppConfig,
        repository: JobRepository | None = None,
        youtube_service: Any | None = None,
    ) -> None:
        self.config = config
        self.repo = repository or JobRepository(config.db_path)
        self._youtube_service = youtube_service

    def _get_youtube_service(self) -> Any:
        if self._youtube_service is not None:
            return self._youtube_service
        creds = get_valid_credentials(
            self.config.token_path,
            client_secrets_path=self.config.client_secrets_path,
            allow_interactive=False,
        )
        self._youtube_service = build_youtube_service(creds)
        return self._youtube_service

    def publish(
        self,
        *,
        video_path: Path,
        metadata_path: Path,
        publish_now: bool = False,
        visibility_override: str | None = None,
        approve: bool = False,
        wait_processing: bool = False,
        related_video_id: str | None = None,
        related_job_id: int | None = None,
    ) -> PublishResult:
        """Execute a full synchronous publishing run for a video + metadata pair."""
        # 1. Wait until files are completely written and readable
        try:
            wait_for_file_ready(
                video_path,
                timeout_seconds=self.config.upload.file_ready_timeout_seconds,
                poll_seconds=self.config.upload.file_ready_poll_seconds,
            )
            wait_for_file_ready(
                metadata_path,
                timeout_seconds=self.config.upload.file_ready_timeout_seconds,
                poll_seconds=self.config.upload.file_ready_poll_seconds,
            )
        except (FileNotFoundError, TimeoutError) as exc:
            return PublishResult(
                success=False,
                exit_code=ExitCode.INVALID_INPUT,
                message=str(exc),
                errors=[str(exc)],
            )

        # 2. Load & validate metadata
        try:
            metadata = load_metadata(
                metadata_path,
                default_category_id=self.config.youtube.category_id,
                default_visibility=self.config.youtube.default_visibility,
                default_tz=self.config.zone_info,
            )
        except MetadataValidationError as exc:
            return PublishResult(
                success=False,
                exit_code=ExitCode.INVALID_INPUT,
                message=f"Metadata validation failed: {exc}",
                errors=list(exc.errors),
            )
        logger.info("Metadata validated.")

        # 2b. Resolve related long-form video (if linking a Short to a long video)
        resolved_related_job_id = (
            related_job_id if related_job_id is not None else metadata.related_job_id
        )
        resolved_related_video_id = related_video_id or metadata.related_video_id
        if not resolved_related_video_id and resolved_related_job_id is not None:
            parent_job = self.repo.get_job(resolved_related_job_id)
            if parent_job is None:
                msg = f"Related job #{resolved_related_job_id} not found in database."
                return PublishResult(
                    success=False,
                    exit_code=ExitCode.INVALID_INPUT,
                    message=msg,
                    errors=[msg],
                )
            if not parent_job.youtube_video_id:
                msg = (
                    f"Related job #{resolved_related_job_id} does not have a YouTube video ID yet "
                    f"(status={parent_job.status.value})."
                )
                return PublishResult(
                    success=False,
                    exit_code=ExitCode.INVALID_INPUT,
                    message=msg,
                    errors=[msg],
                )
            resolved_related_video_id = parent_job.youtube_video_id

        if resolved_related_video_id:
            related_url = f"https://www.youtube.com/watch?v={resolved_related_video_id}"
            if resolved_related_video_id not in metadata.description:
                prefix = f"{metadata.description.rstrip()}\n\n" if metadata.description.strip() else ""
                updated_desc = f"{prefix}Watch the full video: {related_url}"
                metadata = replace(
                    metadata,
                    description=updated_desc,
                    related_video_id=resolved_related_video_id,
                    related_job_id=resolved_related_job_id,
                )
            logger.info("Linked to related video: %s", related_url)

        # 3. Resolve publication & safety policy before uploading
        try:
            plan = resolve_publication_plan(
                metadata,
                safety=self.config.safety,
                tz=self.config.zone_info,
                publish_now=publish_now,
                visibility_override=visibility_override,
                approve=approve,
            )
        except ApprovalRequiredError as exc:
            return PublishResult(
                success=False,
                exit_code=ExitCode.REQUIRES_APPROVAL,
                message=str(exc),
                errors=[str(exc)],
            )
        except SchedulingError as exc:
            return PublishResult(
                success=False,
                exit_code=ExitCode.INVALID_INPUT,
                message=str(exc),
                errors=[str(exc)],
            )

        # 4. Validate video and thumbnail via FFprobe & Pillow
        logger.info("Validating video...")
        validation = validate_video(
            video_path,
            expected_type=metadata.video_type,
            thumbnail_path=metadata.thumbnail,
        )
        for warning in validation.warnings:
            logger.warning("Validation warning: %s", warning)
        if not validation.valid:
            return PublishResult(
                success=False,
                exit_code=ExitCode.INVALID_INPUT,
                message="Video validation failed: " + "; ".join(validation.errors),
                warnings=validation.warnings,
                errors=validation.errors,
            )

        # 5. Duplicate detection via SHA-256
        sha256_hash = compute_sha256(video_path)
        if self.config.upload.prevent_duplicates:
            existing = self.repo.get_job_by_hash(sha256_hash)
            if existing is not None:
                return PublishResult(
                    success=False,
                    exit_code=ExitCode.DUPLICATE_VIDEO,
                    job_id=existing.id,
                    video_id=existing.youtube_video_id,
                    url=existing.video_url,
                    status=existing.status.value,
                    message=(
                        f"Duplicate video detected (matches job #{existing.id}, "
                        f"status={existing.status.value})."
                    ),
                    warnings=validation.warnings,
                )

        # 6. Create persistent job record
        try:
            job = self.repo.create_job(
                video_path=str(video_path.resolve()),
                metadata_path=str(metadata_path.resolve()),
                sha256_hash=sha256_hash,
                title=metadata.title,
                video_type=metadata.video_type,
                visibility=plan.privacy_status,
                publish_at=plan.publish_at_utc,
                thumbnail_path=str(metadata.thumbnail.resolve()) if metadata.thumbnail else None,
                playlist_id=metadata.playlist_id,
                related_video_id=resolved_related_video_id,
                related_job_id=resolved_related_job_id,
                status=JobStatus.VALIDATING,
            )
        except DuplicateJobError as exc:
            return PublishResult(
                success=False,
                exit_code=ExitCode.DUPLICATE_VIDEO,
                job_id=exc.existing_job.id,
                video_id=exc.existing_job.youtube_video_id,
                url=exc.existing_job.video_url,
                status=exc.existing_job.status.value,
                message=str(exc),
                warnings=validation.warnings,
            )

        return self._execute_job_operations(
            job=job,
            metadata=metadata,
            plan=plan,
            wait_processing=wait_processing,
            warnings=validation.warnings,
        )

    def retry_job(
        self,
        job_id: int,
        *,
        approve: bool = False,
        wait_processing: bool = False,
    ) -> PublishResult:
        """Resume an incomplete or failed job without repeating completed operations."""
        job = self.repo.get_job(job_id)
        if job is None:
            return PublishResult(
                success=False,
                exit_code=ExitCode.INVALID_INPUT,
                message=f"Job #{job_id} not found.",
            )

        if job.status == JobStatus.NEEDS_ATTENTION and not job.youtube_video_id:
            return PublishResult(
                success=False,
                exit_code=ExitCode.UPLOAD_FAILURE,
                job_id=job.id,
                status=job.status.value,
                message=(
                    f"Job #{job.id} requires manual reconciliation before retrying because the "
                    "previous upload outcome was uncertain. Check YouTube Studio to confirm "
                    "whether the video was uploaded."
                ),
            )

        metadata_path = Path(job.metadata_path)
        try:
            metadata = load_metadata(
                metadata_path,
                default_category_id=self.config.youtube.category_id,
                default_visibility=self.config.youtube.default_visibility,
                default_tz=self.config.zone_info,
            )
        except MetadataValidationError as exc:
            return PublishResult(
                success=False,
                exit_code=ExitCode.INVALID_INPUT,
                job_id=job.id,
                message=f"Cannot retry job #{job.id}: metadata invalid: {exc}",
                errors=list(exc.errors),
            )

        # Reconstruct plan from persisted job fields if already uploaded, or resolve freshly
        if job.youtube_video_id:
            final_status = (
                "scheduled"
                if job.publish_at
                else ("published" if job.visibility == "public" else "uploaded")
            )
            plan = PublicationPlan(
                privacy_status=job.visibility or "private",
                publish_at_utc=job.publish_at,
                is_scheduled=bool(job.publish_at),
                final_job_status=final_status,
            )
        else:
            try:
                plan = resolve_publication_plan(
                    metadata,
                    safety=self.config.safety,
                    tz=self.config.zone_info,
                    visibility_override=job.visibility if not job.publish_at else None,
                    approve=approve,
                )
            except ApprovalRequiredError as exc:
                return PublishResult(
                    success=False,
                    exit_code=ExitCode.REQUIRES_APPROVAL,
                    job_id=job.id,
                    message=str(exc),
                )
            except SchedulingError as exc:
                return PublishResult(
                    success=False,
                    exit_code=ExitCode.INVALID_INPUT,
                    job_id=job.id,
                    message=str(exc),
                )

        return self._execute_job_operations(
            job=job,
            metadata=metadata,
            plan=plan,
            wait_processing=wait_processing,
            warnings=[],
        )

    def _execute_job_operations(
        self,
        *,
        job: UploadJob,
        metadata: VideoMetadata,
        plan: PublicationPlan,
        wait_processing: bool,
        warnings: list[str],
    ) -> PublishResult:
        try:
            youtube = self._get_youtube_service()
        except AuthenticationError as exc:
            self.repo.update_job_status(job.id, JobStatus.FAILED, error_details=str(exc))
            return PublishResult(
                success=False,
                exit_code=ExitCode.AUTH_FAILURE,
                job_id=job.id,
                video_id=job.youtube_video_id,
                url=job.video_url,
                status=JobStatus.FAILED.value,
                message=str(exc),
                warnings=warnings,
                errors=[str(exc)],
            )

        ops = self.repo.get_operations(job.id)
        video_id = job.youtube_video_id

        # Step A: Video Upload (NEVER repeat if video_id is already persisted)
        if not video_id:
            self.repo.update_job_status(job.id, JobStatus.UPLOADING)
            self.repo.update_operation(
                job.id,
                OperationType.VIDEO_UPLOAD,
                OperationStatus.IN_PROGRESS,
                increment_attempts=True,
            )
            logger.info("Upload started.")
            try:
                video_id = upload_video_resumable(
                    youtube,
                    Path(job.video_path),
                    metadata,
                    plan,
                    chunk_size_bytes=self.config.upload.chunk_size_bytes,
                    max_retries=self.config.upload.max_retries,
                    resumable_uri=job.resumable_uri,
                    on_progress=lambda pct: self.repo.update_upload_progress(job.id, pct),
                    on_resumable_uri=lambda uri: self.repo.save_resumable_uri(job.id, uri),
                )
            except UncertainUploadError as exc:
                self.repo.update_operation(
                    job.id,
                    OperationType.VIDEO_UPLOAD,
                    OperationStatus.NEEDS_ATTENTION,
                    last_error=str(exc),
                )
                self.repo.update_job_status(
                    job.id, JobStatus.NEEDS_ATTENTION, error_details=str(exc)
                )
                return PublishResult(
                    success=False,
                    exit_code=ExitCode.UPLOAD_FAILURE,
                    job_id=job.id,
                    status=JobStatus.NEEDS_ATTENTION.value,
                    message=str(exc),
                    warnings=warnings,
                    errors=[str(exc)],
                )
            except UploadError as exc:
                self.repo.update_operation(
                    job.id,
                    OperationType.VIDEO_UPLOAD,
                    OperationStatus.FAILED,
                    last_error=str(exc),
                )
                self.repo.update_job_status(job.id, JobStatus.FAILED, error_details=str(exc))
                return PublishResult(
                    success=False,
                    exit_code=ExitCode.UPLOAD_FAILURE,
                    job_id=job.id,
                    status=JobStatus.FAILED.value,
                    message=str(exc),
                    warnings=warnings,
                    errors=[str(exc)],
                )

            # Immediately persist YouTube video ID before any subsequent step
            self.repo.record_youtube_video_id(job.id, video_id)
            self.repo.update_operation(
                job.id, OperationType.VIDEO_UPLOAD, OperationStatus.COMPLETED
            )
            self.repo.update_job_status(job.id, JobStatus.UPLOADED, upload_progress=100.0)
        else:
            logger.info(
                "Skipping video upload for job #%d; already uploaded as %s.",
                job.id,
                video_id,
            )

        video_url = f"https://www.youtube.com/watch?v={video_id}"

        # Step B: Thumbnail Upload
        thumb_op = ops.get(OperationType.THUMBNAIL_UPLOAD)
        if (
            job.thumbnail_path
            and thumb_op is not None
            and thumb_op.status not in {OperationStatus.COMPLETED, OperationStatus.SKIPPED}
        ):
            self.repo.update_operation(
                job.id,
                OperationType.THUMBNAIL_UPLOAD,
                OperationStatus.IN_PROGRESS,
                increment_attempts=True,
            )
            try:
                set_video_thumbnail(
                    youtube,
                    video_id,
                    Path(job.thumbnail_path),
                    max_retries=self.config.upload.max_retries,
                )
                self.repo.update_operation(
                    job.id, OperationType.THUMBNAIL_UPLOAD, OperationStatus.COMPLETED
                )
            except Exception as exc:
                err_msg = f"Thumbnail upload failed (video {video_id} is already uploaded): {exc}"
                self.repo.update_operation(
                    job.id,
                    OperationType.THUMBNAIL_UPLOAD,
                    OperationStatus.FAILED,
                    last_error=str(exc),
                )
                self.repo.update_job_status(job.id, JobStatus.FAILED, error_details=err_msg)
                return PublishResult(
                    success=False,
                    exit_code=ExitCode.UPLOAD_FAILURE,
                    job_id=job.id,
                    video_id=video_id,
                    url=video_url,
                    status=JobStatus.FAILED.value,
                    message=err_msg,
                    warnings=warnings,
                    errors=[err_msg],
                )

        # Step C: Playlist Insertion
        playlist_op = ops.get(OperationType.PLAYLIST_INSERT)
        if (
            job.playlist_id
            and playlist_op is not None
            and playlist_op.status not in {OperationStatus.COMPLETED, OperationStatus.SKIPPED}
        ):
            self.repo.update_operation(
                job.id,
                OperationType.PLAYLIST_INSERT,
                OperationStatus.IN_PROGRESS,
                increment_attempts=True,
            )
            try:
                add_video_to_playlist(
                    youtube,
                    video_id,
                    job.playlist_id,
                    max_retries=self.config.upload.max_retries,
                )
                self.repo.update_operation(
                    job.id, OperationType.PLAYLIST_INSERT, OperationStatus.COMPLETED
                )
            except Exception as exc:
                err_msg = (
                    f"Playlist insertion failed (video {video_id} is already uploaded): {exc}"
                )
                self.repo.update_operation(
                    job.id,
                    OperationType.PLAYLIST_INSERT,
                    OperationStatus.FAILED,
                    last_error=str(exc),
                )
                self.repo.update_job_status(job.id, JobStatus.FAILED, error_details=err_msg)
                return PublishResult(
                    success=False,
                    exit_code=ExitCode.UPLOAD_FAILURE,
                    job_id=job.id,
                    video_id=video_id,
                    url=video_url,
                    status=JobStatus.FAILED.value,
                    message=err_msg,
                    warnings=warnings,
                    errors=[err_msg],
                )

        # Step D: YouTube Processing Verification
        verify_op = ops.get(OperationType.PROCESSING_VERIFICATION)
        if verify_op is not None and verify_op.status != OperationStatus.COMPLETED:
            self.repo.update_operation(
                job.id,
                OperationType.PROCESSING_VERIFICATION,
                OperationStatus.IN_PROGRESS,
                increment_attempts=True,
            )
            try:
                if wait_processing:
                    self.repo.update_job_status(job.id, JobStatus.PROCESSING)
                    details = wait_for_processing(youtube, video_id)
                else:
                    details = get_video_details(youtube, video_id) or {}
                self.repo.update_operation(
                    job.id, OperationType.PROCESSING_VERIFICATION, OperationStatus.COMPLETED
                )
                upload_status = (details.get("status") or {}).get("uploadStatus")
                if upload_status in {"failed", "rejected"}:
                    err_msg = f"YouTube reported uploadStatus={upload_status!r} for {video_id}."
                    self.repo.update_job_status(
                        job.id, JobStatus.FAILED, error_details=err_msg
                    )
                    return PublishResult(
                        success=False,
                        exit_code=ExitCode.UPLOAD_FAILURE,
                        job_id=job.id,
                        video_id=video_id,
                        url=video_url,
                        status=JobStatus.FAILED.value,
                        message=err_msg,
                        warnings=warnings,
                        errors=[err_msg],
                    )
            except Exception as exc:
                # Non-fatal if video is already uploaded, but record as pending/failed verification
                self.repo.update_operation(
                    job.id,
                    OperationType.PROCESSING_VERIFICATION,
                    OperationStatus.FAILED,
                    last_error=str(exc),
                )
                warnings.append(f"Processing verification could not complete: {exc}")

        final_status = JobStatus(plan.final_job_status)
        self.repo.update_job_status(job.id, final_status, error_details=None)

        if final_status == JobStatus.SCHEDULED:
            msg = f"Video uploaded and scheduled successfully for {plan.publish_at_utc}."
        elif final_status == JobStatus.PUBLISHED:
            msg = "Video uploaded and published successfully."
        else:
            msg = f"Video uploaded successfully ({plan.privacy_status})."

        related_vid = job.related_video_id
        related_url = f"https://www.youtube.com/watch?v={related_vid}" if related_vid else None
        studio_edit_url = (
            f"https://studio.youtube.com/video/{video_id}/edit" if related_vid else None
        )

        return PublishResult(
            success=True,
            exit_code=ExitCode.SUCCESS,
            job_id=job.id,
            video_id=video_id,
            url=video_url,
            status=final_status.value,
            related_video_id=related_vid,
            related_video_url=related_url,
            studio_edit_url=studio_edit_url,
            message=msg,
            warnings=warnings,
        )
