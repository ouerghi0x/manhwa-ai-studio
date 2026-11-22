"""Scheduling and publication safety policy resolution."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from publisher.config import SafetyConfig
from publisher.core.metadata import VideoMetadata


class SchedulingError(ValueError):
    """Raised when scheduling parameters are invalid (e.g., past publish_at)."""


class ApprovalRequiredError(PermissionError):
    """Raised when safety policy blocks public or scheduled publication without approval."""


@dataclass(frozen=True)
class PublicationPlan:
    """Resolved YouTube privacy and scheduling parameters."""

    privacy_status: str  # "private", "unlisted", or "public"
    publish_at_utc: str | None  # RFC 3339 UTC string for YouTube API, or None
    is_scheduled: bool
    final_job_status: str  # "scheduled" or "published" or "uploaded"


def resolve_publication_plan(
    metadata: VideoMetadata,
    *,
    safety: SafetyConfig,
    tz: ZoneInfo,
    publish_now: bool = False,
    visibility_override: str | None = None,
    approve: bool = False,
    now_utc: datetime | None = None,
) -> PublicationPlan:
    """Resolve final YouTube privacyStatus and publishAt according to CLI flags & safety policy.

    Rules:
    - YouTube Data API v3 requires privacyStatus='private' whenever publishAt is set.
    - If --now is passed, publish immediately (no publishAt) using visibility_override or 'public'.
    - If --visibility private is explicitly passed without --now, upload privately without scheduling.
    - Public or scheduled publication is blocked if safety.allow_publication is False or if
      safety.require_approval is True and --approve was not supplied.
    """
    current_utc = now_utc or datetime.now(timezone.utc)

    if visibility_override is not None and visibility_override not in {
        "private",
        "unlisted",
        "public",
    }:
        raise SchedulingError(f"Invalid visibility override: {visibility_override!r}")

    if publish_now:
        target_visibility = visibility_override or "public"
        if target_visibility == "public":
            _enforce_publication_policy(safety=safety, approve=approve, reason="immediate public publication")
        return PublicationPlan(
            privacy_status=target_visibility,
            publish_at_utc=None,
            is_scheduled=False,
            final_job_status="published" if target_visibility == "public" else "uploaded",
        )

    # Explicit --visibility private disables scheduling for this run.
    if visibility_override == "private":
        return PublicationPlan(
            privacy_status="private",
            publish_at_utc=None,
            is_scheduled=False,
            final_job_status="uploaded",
        )

    if visibility_override == "unlisted":
        return PublicationPlan(
            privacy_status="unlisted",
            publish_at_utc=None,
            is_scheduled=False,
            final_job_status="uploaded",
        )

    if visibility_override == "public":
        _enforce_publication_policy(safety=safety, approve=approve, reason="public publication")
        return PublicationPlan(
            privacy_status="public",
            publish_at_utc=None,
            is_scheduled=False,
            final_job_status="published",
        )

    # No CLI override: follow metadata.publish_at if present, else metadata.visibility.
    if metadata.publish_at is not None:
        scheduled_dt = metadata.publish_at
        if scheduled_dt.tzinfo is None:
            scheduled_dt = scheduled_dt.replace(tzinfo=tz)
        scheduled_utc = scheduled_dt.astimezone(timezone.utc)
        if scheduled_utc <= current_utc:
            raise SchedulingError(
                f"Scheduled publish_at ({scheduled_dt.isoformat()}) must be in the future."
            )
        _enforce_publication_policy(
            safety=safety,
            approve=approve,
            reason=f"scheduled public publication at {scheduled_dt.isoformat()}",
        )
        rfc3339 = scheduled_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
        return PublicationPlan(
            privacy_status="private",  # Required by YouTube Data API v3 for scheduled videos
            publish_at_utc=rfc3339,
            is_scheduled=True,
            final_job_status="scheduled",
        )

    if metadata.visibility == "public":
        _enforce_publication_policy(safety=safety, approve=approve, reason="public publication")
        return PublicationPlan(
            privacy_status="public",
            publish_at_utc=None,
            is_scheduled=False,
            final_job_status="published",
        )

    return PublicationPlan(
        privacy_status=metadata.visibility,
        publish_at_utc=None,
        is_scheduled=False,
        final_job_status="uploaded",
    )


def _enforce_publication_policy(*, safety: SafetyConfig, approve: bool, reason: str) -> None:
    if not safety.allow_publication:
        raise ApprovalRequiredError(
            f"Publication policy blocks {reason} (safety.allow_publication is false)."
        )
    if safety.require_approval and not approve:
        raise ApprovalRequiredError(
            f"Manual approval required for {reason}. Re-run with --approve or upload with "
            "--visibility private."
        )
