"""Command-line interface for manhwa-publisher."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from publisher import __version__
from publisher.config import AppConfig, load_config
from publisher.core.metadata import MetadataValidationError, load_metadata
from publisher.core.pipeline import PublishingPipeline
from publisher.core.validator import check_ffprobe_available, validate_video
from publisher.database.repository import JobRepository
from publisher.exit_codes import ExitCode
from publisher.utils.logger import setup_logging
from publisher.youtube.auth import (
    AuthenticationError,
    authenticate_interactive,
    build_youtube_service,
    get_valid_credentials,
)
from publisher.youtube.videos import get_authenticated_channel, get_video_details


def _emit_json(payload: dict[str, Any]) -> None:
    """Print exactly one machine-readable JSON object to stdout."""
    sys.stdout.write(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    sys.stdout.flush()


def _add_common_flags(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help="Path to config.yaml (defaults to ./config.yaml).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="json_mode",
        help="Emit a single machine-readable JSON object to stdout (logs go to stderr).",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m publisher",
        description="Manhwa Publisher — Autonomous YouTube Publishing CLI",
    )
    parser.add_argument("--version", action="version", version=f"manhwa-publisher {__version__}")

    subparsers = parser.add_subparsers(dest="command", required=True)

    # publish
    p_pub = subparsers.add_parser("publish", help="Validate, upload, and publish/schedule a video.")
    p_pub.add_argument("--video", required=True, type=Path, help="Path to the MP4/video file.")
    p_pub.add_argument("--metadata", required=True, type=Path, help="Path to metadata JSON file.")
    p_pub.add_argument(
        "--now",
        action="store_true",
        dest="publish_now",
        help="Publish immediately instead of using publish_at scheduling.",
    )
    p_pub.add_argument(
        "--visibility",
        choices=["private", "unlisted", "public"],
        default=None,
        help="Override video visibility (private, unlisted, public).",
    )
    p_pub.add_argument(
        "--approve",
        action="store_true",
        help="Explicitly approve public or scheduled publication when require_approval is enabled.",
    )
    p_pub.add_argument(
        "--wait-processing",
        action="store_true",
        help="Wait until YouTube finishes processing the uploaded video.",
    )
    p_pub.add_argument(
        "--related-video-id",
        type=str,
        default=None,
        help="YouTube video ID of the related long-form video (auto-linked in Short description).",
    )
    p_pub.add_argument(
        "--related-job-id",
        type=int,
        default=None,
        help="Local SQLite job ID of the related long-form video (resolves its YouTube video ID).",
    )
    _add_common_flags(p_pub)

    # validate
    p_val = subparsers.add_parser("validate", help="Validate video, thumbnail, and metadata.")
    p_val.add_argument("--video", required=True, type=Path, help="Path to the video file.")
    p_val.add_argument("--metadata", required=True, type=Path, help="Path to metadata JSON file.")
    _add_common_flags(p_val)

    # status
    p_stat = subparsers.add_parser("status", help="Inspect upload history or a specific video.")
    p_stat.add_argument("--video-id", type=str, default=None, help="Filter by YouTube video ID.")
    p_stat.add_argument("--job-id", type=int, default=None, help="Filter by local job ID.")
    p_stat.add_argument(
        "--remote",
        action="store_true",
        help="Also query YouTube Data API v3 for live processing status.",
    )
    p_stat.add_argument("--limit", type=int, default=20, help="Max jobs to display.")
    _add_common_flags(p_stat)

    # queue
    p_queue = subparsers.add_parser("queue", help="List pending, failed, or in-progress jobs.")
    p_queue.add_argument("--limit", type=int, default=50, help="Max jobs to display.")
    _add_common_flags(p_queue)

    # retry
    p_retry = subparsers.add_parser("retry", help="Retry incomplete operations for a job.")
    p_retry.add_argument("job_id", type=int, help="Numeric job ID to retry.")
    p_retry.add_argument(
        "--approve",
        action="store_true",
        help="Approve public/scheduled publication if required.",
    )
    p_retry.add_argument(
        "--wait-processing",
        action="store_true",
        help="Wait until YouTube finishes processing.",
    )
    _add_common_flags(p_retry)

    # auth
    p_auth = subparsers.add_parser("auth", help="Authenticate YouTube channel via OAuth 2.0.")
    p_auth.add_argument("--port", type=int, default=0, help="Local callback server port.")
    p_auth.add_argument(
        "--no-browser",
        action="store_true",
        help="Do not automatically open a browser window.",
    )
    _add_common_flags(p_auth)

    # doctor
    p_doc = subparsers.add_parser("doctor", help="Check FFprobe, DB, OAuth, and YouTube API.")
    _add_common_flags(p_doc)

    return parser


def _cmd_publish(args: argparse.Namespace, config: AppConfig) -> int:
    pipeline = PublishingPipeline(config)
    result = pipeline.publish(
        video_path=args.video,
        metadata_path=args.metadata,
        publish_now=args.publish_now,
        visibility_override=args.visibility,
        approve=args.approve,
        wait_processing=args.wait_processing,
        related_video_id=args.related_video_id,
        related_job_id=args.related_job_id,
    )
    if args.json_mode:
        _emit_json(result.to_dict())
    else:
        if result.success:
            print(f"\n[SUCCESS] {result.message}")
            if result.video_id:
                print(f"Video ID: {result.video_id}")
            if result.url:
                print(f"URL: {result.url}")
            if result.job_id is not None:
                print(f"Job ID: {result.job_id}")
            if result.related_video_url:
                print(f"Related Video: {result.related_video_url}")
            if result.studio_edit_url:
                print(
                    f"YouTube Studio (to set native Shorts 'Related video' button): "
                    f"{result.studio_edit_url}"
                )
        else:
            print(f"\n[ERROR] {result.message}", file=sys.stderr)
    return int(result.exit_code)


def _cmd_validate(args: argparse.Namespace, config: AppConfig) -> int:
    try:
        metadata = load_metadata(
            args.metadata,
            default_category_id=config.youtube.category_id,
            default_visibility=config.youtube.default_visibility,
            default_tz=config.zone_info,
        )
    except MetadataValidationError as exc:
        payload = {
            "success": False,
            "valid": False,
            "errors": exc.errors,
            "warnings": [],
            "message": f"Metadata validation failed: {exc}",
        }
        if args.json_mode:
            _emit_json(payload)
        else:
            print(f"[ERROR] {payload['message']}", file=sys.stderr)
        return int(ExitCode.INVALID_INPUT)

    val = validate_video(
        args.video,
        expected_type=metadata.video_type,
        thumbnail_path=metadata.thumbnail,
    )
    payload = {
        "success": val.valid,
        "valid": val.valid,
        "metadata": metadata.to_dict(),
        "validation": val.to_dict(),
        "message": "Validation passed." if val.valid else "Validation failed.",
    }
    if args.json_mode:
        _emit_json(payload)
    else:
        for w in val.warnings:
            print(f"[WARNING] {w}")
        if val.valid:
            print("[SUCCESS] Video and metadata are valid.")
        else:
            for e in val.errors:
                print(f"[ERROR] {e}", file=sys.stderr)
    return int(ExitCode.SUCCESS if val.valid else ExitCode.INVALID_INPUT)


def _cmd_status(args: argparse.Namespace, config: AppConfig) -> int:
    repo = JobRepository(config.db_path)

    if args.video_id:
        job = repo.get_job_by_video_id(args.video_id)
        remote_info: dict[str, Any] | None = None
        if args.remote:
            try:
                creds = get_valid_credentials(config.token_path)
                yt = build_youtube_service(creds)
                remote_info = get_video_details(yt, args.video_id)
            except AuthenticationError as exc:
                if args.json_mode:
                    _emit_json({"success": False, "message": str(exc)})
                else:
                    print(f"[ERROR] {exc}", file=sys.stderr)
                return int(ExitCode.AUTH_FAILURE)

        if job is None and remote_info is None:
            msg = f"No record found for video_id={args.video_id!r}."
            if args.json_mode:
                _emit_json({"success": False, "message": msg})
            else:
                print(f"[ERROR] {msg}", file=sys.stderr)
            return int(ExitCode.INVALID_INPUT)

        ops = (
            {k.value: v.to_dict() for k, v in repo.get_operations(job.id).items()}
            if job is not None
            else {}
        )
        payload = {
            "success": True,
            "job": job.to_dict() if job else None,
            "operations": ops,
            "remote": remote_info,
        }
        if args.json_mode:
            _emit_json(payload)
        else:
            if job:
                print(
                    f"Job #{job.id} | status={job.status.value} | "
                    f"video_id={job.youtube_video_id} | url={job.video_url}"
                )
            if remote_info:
                st = remote_info.get("status") or {}
                print(
                    f"YouTube Live: uploadStatus={st.get('uploadStatus')}, "
                    f"privacyStatus={st.get('privacyStatus')}"
                )
        return int(ExitCode.SUCCESS)

    if args.job_id is not None:
        job = repo.get_job(args.job_id)
        if job is None:
            msg = f"Job #{args.job_id} not found."
            if args.json_mode:
                _emit_json({"success": False, "message": msg})
            else:
                print(f"[ERROR] {msg}", file=sys.stderr)
            return int(ExitCode.INVALID_INPUT)
        ops = {k.value: v.to_dict() for k, v in repo.get_operations(job.id).items()}
        payload = {"success": True, "job": job.to_dict(), "operations": ops}
        if args.json_mode:
            _emit_json(payload)
        else:
            print(
                f"Job #{job.id} | status={job.status.value} | "
                f"progress={job.upload_progress:.1f}% | video_id={job.youtube_video_id}"
            )
        return int(ExitCode.SUCCESS)

    jobs = repo.list_jobs(limit=args.limit)
    payload = {"success": True, "count": len(jobs), "jobs": [j.to_dict() for j in jobs]}
    if args.json_mode:
        _emit_json(payload)
    else:
        if not jobs:
            print("No upload jobs recorded yet.")
        for j in jobs:
            print(
                f"#{j.id:<4} {j.status.value:<15} {j.upload_progress:5.1f}%  "
                f"{j.youtube_video_id or '-':<13} {j.title or j.video_path}"
            )
    return int(ExitCode.SUCCESS)


def _cmd_queue(args: argparse.Namespace, config: AppConfig) -> int:
    repo = JobRepository(config.db_path)
    jobs = repo.list_pending_queue(limit=args.limit)
    payload = {"success": True, "count": len(jobs), "jobs": [j.to_dict() for j in jobs]}
    if args.json_mode:
        _emit_json(payload)
    else:
        if not jobs:
            print("No pending or failed jobs in queue.")
        for j in jobs:
            print(
                f"#{j.id:<4} {j.status.value:<15} {j.upload_progress:5.1f}%  "
                f"{j.title or j.video_path}  err={j.error_details or '-'}"
            )
    return int(ExitCode.SUCCESS)


def _cmd_retry(args: argparse.Namespace, config: AppConfig) -> int:
    pipeline = PublishingPipeline(config)
    result = pipeline.retry_job(
        args.job_id,
        approve=args.approve,
        wait_processing=args.wait_processing,
    )
    if args.json_mode:
        _emit_json(result.to_dict())
    else:
        if result.success:
            print(f"\n[SUCCESS] {result.message}")
            if result.video_id:
                print(f"Video ID: {result.video_id}")
        else:
            print(f"\n[ERROR] {result.message}", file=sys.stderr)
    return int(result.exit_code)


def _cmd_auth(args: argparse.Namespace, config: AppConfig) -> int:
    try:
        authenticate_interactive(
            config.client_secrets_path,
            config.token_path,
            port=args.port,
            open_browser=not args.no_browser,
        )
    except AuthenticationError as exc:
        if args.json_mode:
            _emit_json({"success": False, "message": str(exc)})
        else:
            print(f"[ERROR] {exc}", file=sys.stderr)
        return int(ExitCode.AUTH_FAILURE)

    payload = {
        "success": True,
        "token_path": str(config.token_path),
        "message": "YouTube OAuth 2.0 authentication completed successfully.",
    }
    if args.json_mode:
        _emit_json(payload)
    else:
        print(f"[SUCCESS] {payload['message']}")
    return int(ExitCode.SUCCESS)


def _cmd_doctor(args: argparse.Namespace, config: AppConfig) -> int:
    checks: dict[str, Any] = {}
    all_ok = True

    ffprobe_path = check_ffprobe_available()
    checks["ffprobe"] = {"ok": ffprobe_path is not None, "path": ffprobe_path}
    if ffprobe_path is None:
        all_ok = False

    try:
        _ = JobRepository(config.db_path)
        checks["database"] = {"ok": True, "path": str(config.db_path)}
    except Exception as exc:
        checks["database"] = {"ok": False, "error": str(exc)}
        all_ok = False

    checks["client_secrets"] = {
        "ok": config.client_secrets_path.exists(),
        "path": str(config.client_secrets_path),
    }

    try:
        creds = get_valid_credentials(config.token_path)
        yt = build_youtube_service(creds)
        channel = get_authenticated_channel(yt)
        if channel:
            snippet = channel.get("snippet") or {}
            checks["youtube_auth"] = {
                "ok": True,
                "channel_id": channel.get("id"),
                "channel_title": snippet.get("title"),
            }
        else:
            checks["youtube_auth"] = {"ok": False, "error": "No YouTube channel found for account."}
            all_ok = False
    except AuthenticationError as exc:
        checks["youtube_auth"] = {"ok": False, "error": str(exc)}
        all_ok = False
    except Exception as exc:
        checks["youtube_auth"] = {"ok": False, "error": str(exc)}
        all_ok = False

    payload = {
        "success": all_ok,
        "checks": checks,
        "message": "All checks passed." if all_ok else "One or more doctor checks failed.",
    }
    if args.json_mode:
        _emit_json(payload)
    else:
        for name, info in checks.items():
            status = "OK" if info.get("ok") else "FAIL"
            print(f"[{status}] {name}: {info}")
    if all_ok:
        return int(ExitCode.SUCCESS)
    if not checks.get("youtube_auth", {}).get("ok"):
        return int(ExitCode.AUTH_FAILURE)
    return int(ExitCode.GENERAL_FAILURE)


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        config = load_config(args.config)
    except Exception as exc:
        if getattr(args, "json_mode", False):
            _emit_json({"success": False, "message": f"Configuration error: {exc}"})
        else:
            print(f"[ERROR] Configuration error: {exc}", file=sys.stderr)
        return int(ExitCode.INVALID_INPUT)

    setup_logging(config.logs_dir, json_mode=bool(getattr(args, "json_mode", False)))

    handlers = {
        "publish": _cmd_publish,
        "validate": _cmd_validate,
        "status": _cmd_status,
        "queue": _cmd_queue,
        "retry": _cmd_retry,
        "auth": _cmd_auth,
        "doctor": _cmd_doctor,
    }
    handler = handlers[args.command]
    return handler(args, config)


if __name__ == "__main__":
    raise SystemExit(main())
