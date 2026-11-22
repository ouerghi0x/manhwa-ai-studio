"""Metadata JSON contract parsing and validation."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

VALID_VIDEO_TYPES = frozenset({"long", "short"})
VALID_VISIBILITIES = frozenset({"private", "unlisted", "public"})
MAX_TITLE_LENGTH = 100
MAX_DESCRIPTION_LENGTH = 5000
MAX_TOTAL_TAGS_CHARS = 500


class MetadataValidationError(ValueError):
    """Raised when a metadata JSON file fails schema or constraint validation."""

    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        super().__init__("; ".join(errors))


@dataclass(frozen=True)
class VideoMetadata:
    """Validated metadata contract for a YouTube video upload."""

    title: str
    video_type: str
    description: str = ""
    tags: list[str] = field(default_factory=list)
    category_id: str = "24"
    language: str = "en"
    thumbnail: Path | None = None
    playlist_id: str | None = None
    visibility: str = "private"
    publish_at: datetime | None = None
    related_video_id: str | None = None
    related_job_id: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "type": self.video_type,
            "description": self.description,
            "tags": list(self.tags),
            "category_id": self.category_id,
            "language": self.language,
            "thumbnail": str(self.thumbnail) if self.thumbnail else None,
            "playlist_id": self.playlist_id,
            "visibility": self.visibility,
            "publish_at": self.publish_at.isoformat() if self.publish_at else None,
            "related_video_id": self.related_video_id,
            "related_job_id": self.related_job_id,
        }


def parse_publish_at(raw_value: str, default_tz: ZoneInfo) -> datetime:
    """Parse an ISO-8601 timestamp into a timezone-aware datetime."""
    cleaned = raw_value.strip()
    if cleaned.endswith("Z"):
        cleaned = cleaned[:-1] + "+00:00"
    dt = datetime.fromisoformat(cleaned)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=default_tz)
    return dt


def load_metadata(
    metadata_path: Path,
    *,
    default_category_id: str = "24",
    default_visibility: str = "private",
    default_tz: ZoneInfo | None = None,
) -> VideoMetadata:
    """Load and validate a metadata JSON file."""
    if not metadata_path.exists():
        raise MetadataValidationError([f"Metadata file not found: {metadata_path}"])
    if not metadata_path.is_file():
        raise MetadataValidationError([f"Metadata path is not a file: {metadata_path}"])

    try:
        raw_text = metadata_path.read_text(encoding="utf-8")
        data = json.loads(raw_text)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise MetadataValidationError([f"Invalid JSON in metadata file: {exc}"]) from exc

    if not isinstance(data, dict):
        raise MetadataValidationError(["Metadata JSON root must be an object."])

    return validate_metadata_dict(
        data,
        base_dir=metadata_path.parent,
        default_category_id=default_category_id,
        default_visibility=default_visibility,
        default_tz=default_tz,
    )


def validate_metadata_dict(
    data: dict[str, Any],
    *,
    base_dir: Path | None = None,
    default_category_id: str = "24",
    default_visibility: str = "private",
    default_tz: ZoneInfo | None = None,
) -> VideoMetadata:
    """Validate a raw metadata dictionary and return a VideoMetadata instance."""
    errors: list[str] = []
    tz = default_tz or ZoneInfo("UTC")

    # Required: title
    raw_title = data.get("title")
    if not isinstance(raw_title, str) or not raw_title.strip():
        errors.append("Missing or empty required field: 'title'.")
        title = ""
    else:
        title = raw_title.strip()
        if len(title) > MAX_TITLE_LENGTH:
            errors.append(
                f"'title' exceeds YouTube maximum length of {MAX_TITLE_LENGTH} characters "
                f"(got {len(title)})."
            )

    # Required: type
    raw_type = data.get("type")
    if not isinstance(raw_type, str) or raw_type.strip().lower() not in VALID_VIDEO_TYPES:
        errors.append(
            f"Missing or invalid required field 'type'. Expected one of: "
            f"{sorted(VALID_VIDEO_TYPES)}."
        )
        video_type = "long"
    else:
        video_type = raw_type.strip().lower()

    # Optional: description
    raw_desc = data.get("description", "")
    if raw_desc is None:
        description = ""
    elif not isinstance(raw_desc, str):
        errors.append("'description' must be a string.")
        description = ""
    else:
        description = raw_desc
        if len(description) > MAX_DESCRIPTION_LENGTH:
            errors.append(
                f"'description' exceeds YouTube maximum length of {MAX_DESCRIPTION_LENGTH} "
                f"characters (got {len(description)})."
            )

    # Optional: tags
    raw_tags = data.get("tags", [])
    tags: list[str] = []
    if raw_tags is None:
        tags = []
    elif not isinstance(raw_tags, list) or not all(isinstance(t, str) for t in raw_tags):
        errors.append("'tags' must be a list of strings.")
    else:
        tags = [t.strip() for t in raw_tags if t.strip()]
        total_chars = sum(len(t) for t in tags)
        if total_chars > MAX_TOTAL_TAGS_CHARS:
            errors.append(
                f"Total length of 'tags' ({total_chars}) exceeds YouTube limit of "
                f"{MAX_TOTAL_TAGS_CHARS} characters."
            )

    # Optional: category_id
    raw_cat = data.get("category_id", default_category_id)
    if raw_cat is None or str(raw_cat).strip() == "":
        category_id = default_category_id
    else:
        category_id = str(raw_cat).strip()
        if not category_id.isdigit():
            errors.append(f"'category_id' must be numeric (got {category_id!r}).")

    # Optional: language
    raw_lang = data.get("language", "en")
    if raw_lang is None:
        language = "en"
    elif not isinstance(raw_lang, str) or not raw_lang.strip():
        errors.append("'language' must be a non-empty string.")
        language = "en"
    else:
        language = raw_lang.strip()

    # Optional: visibility
    raw_vis = data.get("visibility", default_visibility)
    if raw_vis is None:
        visibility = default_visibility
    elif not isinstance(raw_vis, str) or raw_vis.strip().lower() not in VALID_VISIBILITIES:
        errors.append(
            f"Invalid 'visibility': {raw_vis!r}. Expected one of: {sorted(VALID_VISIBILITIES)}."
        )
        visibility = default_visibility
    else:
        visibility = raw_vis.strip().lower()

    # Optional: thumbnail
    raw_thumb = data.get("thumbnail")
    thumbnail: Path | None = None
    if raw_thumb is not None and raw_thumb != "":
        if not isinstance(raw_thumb, str):
            errors.append("'thumbnail' must be a file path string.")
        else:
            p = Path(raw_thumb)
            if not p.is_absolute():
                # Prefer relative to CWD if it exists, otherwise relative to metadata file dir.
                cwd_candidate = (Path.cwd() / p).resolve()
                if cwd_candidate.exists():
                    p = cwd_candidate
                elif base_dir is not None:
                    p = (base_dir / p).resolve()
                else:
                    p = cwd_candidate
            thumbnail = p

    # Optional: playlist_id
    raw_playlist = data.get("playlist_id")
    playlist_id: str | None = None
    if raw_playlist is not None and raw_playlist != "":
        if not isinstance(raw_playlist, str) or not raw_playlist.strip():
            errors.append("'playlist_id' must be a non-empty string when provided.")
        else:
            playlist_id = raw_playlist.strip()

    # Optional: publish_at
    raw_publish_at = data.get("publish_at")
    publish_at: datetime | None = None
    if raw_publish_at is not None and raw_publish_at != "":
        if not isinstance(raw_publish_at, str):
            errors.append("'publish_at' must be an ISO-8601 datetime string.")
        else:
            try:
                publish_at = parse_publish_at(raw_publish_at, tz)
            except ValueError as exc:
                errors.append(f"Invalid 'publish_at' timestamp {raw_publish_at!r}: {exc}")

    # Optional: related_video_id
    raw_related_vid = data.get("related_video_id")
    related_video_id: str | None = None
    if raw_related_vid is not None and raw_related_vid != "":
        if not isinstance(raw_related_vid, str) or not raw_related_vid.strip():
            errors.append("'related_video_id' must be a non-empty string when provided.")
        else:
            related_video_id = raw_related_vid.strip()

    # Optional: related_job_id
    raw_related_job = data.get("related_job_id")
    related_job_id: int | None = None
    if raw_related_job is not None and raw_related_job != "":
        if isinstance(raw_related_job, bool) or not isinstance(raw_related_job, int) or raw_related_job <= 0:
            errors.append("'related_job_id' must be a positive integer when provided.")
        else:
            related_job_id = raw_related_job

    if errors:
        raise MetadataValidationError(errors)

    return VideoMetadata(
        title=title,
        video_type=video_type,
        description=description,
        tags=tags,
        category_id=category_id,
        language=language,
        thumbnail=thumbnail,
        playlist_id=playlist_id,
        visibility=visibility,
        publish_at=publish_at,
        related_video_id=related_video_id,
        related_job_id=related_job_id,
    )
