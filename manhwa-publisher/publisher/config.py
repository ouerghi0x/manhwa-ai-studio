"""YAML configuration loader with sensible defaults and environment overrides."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import yaml


@dataclass(frozen=True)
class YouTubeConfig:
    category_id: str = "24"
    default_visibility: str = "private"


@dataclass(frozen=True)
class UploadConfig:
    chunk_size_mb: int = 8
    max_retries: int = 8
    prevent_duplicates: bool = True
    resumable: bool = True
    file_ready_timeout_seconds: float = 60.0
    file_ready_poll_seconds: float = 1.0

    @property
    def chunk_size_bytes(self) -> int:
        # YouTube resumable uploads require chunk sizes to be multiples of 256 KB.
        mb = max(1, self.chunk_size_mb)
        return mb * 1024 * 1024


@dataclass(frozen=True)
class DatabaseConfig:
    path: str = "data/publisher.db"


@dataclass(frozen=True)
class PathsConfig:
    logs: str = "logs"
    credentials: str = "credentials"
    client_secrets_file: str = "client_secrets.json"
    token_file: str = "token.json"


@dataclass(frozen=True)
class SafetyConfig:
    require_approval: bool = True
    allow_publication: bool = True


@dataclass(frozen=True)
class AppConfig:
    base_dir: Path = field(default_factory=lambda: Path.cwd())
    youtube: YouTubeConfig = field(default_factory=YouTubeConfig)
    upload: UploadConfig = field(default_factory=UploadConfig)
    timezone: str = "Africa/Tunis"
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    paths: PathsConfig = field(default_factory=PathsConfig)
    safety: SafetyConfig = field(default_factory=SafetyConfig)

    def resolve_path(self, raw_path: str | Path) -> Path:
        p = Path(raw_path)
        if p.is_absolute():
            return p
        return (self.base_dir / p).resolve()

    @property
    def db_path(self) -> Path:
        return self.resolve_path(self.database.path)

    @property
    def logs_dir(self) -> Path:
        return self.resolve_path(self.paths.logs)

    @property
    def credentials_dir(self) -> Path:
        return self.resolve_path(self.paths.credentials)

    @property
    def client_secrets_path(self) -> Path:
        return self.credentials_dir / self.paths.client_secrets_file

    @property
    def token_path(self) -> Path:
        return self.credentials_dir / self.paths.token_file

    @property
    def zone_info(self) -> ZoneInfo:
        try:
            return ZoneInfo(self.timezone)
        except ZoneInfoNotFoundError as exc:
            raise ValueError(f"Invalid timezone in configuration: {self.timezone!r}") from exc


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ValueError(f"Configuration file {path} must contain a YAML mapping.")
    return data


def load_config(config_path: str | Path | None = None) -> AppConfig:
    """Load configuration from YAML with sensible defaults and env overrides."""
    env_config = os.environ.get("MANHWA_PUBLISHER_CONFIG")
    if config_path is not None:
        cfg_file = Path(config_path).resolve()
        base_dir = cfg_file.parent
    elif env_config:
        cfg_file = Path(env_config).resolve()
        base_dir = cfg_file.parent
    else:
        cwd_cfg = Path.cwd() / "config.yaml"
        pkg_cfg = Path(__file__).resolve().parent.parent / "config.yaml"
        if cwd_cfg.exists():
            cfg_file = cwd_cfg
            base_dir = cwd_cfg.parent
        elif pkg_cfg.exists():
            cfg_file = pkg_cfg
            base_dir = pkg_cfg.parent
        else:
            cfg_file = cwd_cfg
            base_dir = Path.cwd()

    raw = _load_yaml(cfg_file)

    yt_raw = raw.get("youtube") or {}
    up_raw = raw.get("upload") or {}
    db_raw = raw.get("database") or {}
    paths_raw = raw.get("paths") or {}
    safety_raw = raw.get("safety") or {}

    youtube_cfg = YouTubeConfig(
        category_id=str(yt_raw.get("category_id", "24")),
        default_visibility=str(yt_raw.get("default_visibility", "private")),
    )
    upload_cfg = UploadConfig(
        chunk_size_mb=int(up_raw.get("chunk_size_mb", 8)),
        max_retries=int(up_raw.get("max_retries", 8)),
        prevent_duplicates=bool(up_raw.get("prevent_duplicates", True)),
        resumable=bool(up_raw.get("resumable", True)),
        file_ready_timeout_seconds=float(up_raw.get("file_ready_timeout_seconds", 60.0)),
        file_ready_poll_seconds=float(up_raw.get("file_ready_poll_seconds", 1.0)),
    )

    db_path = os.environ.get("MANHWA_PUBLISHER_DB_PATH") or str(
        db_raw.get("path", "data/publisher.db")
    )
    creds_dir = os.environ.get("MANHWA_PUBLISHER_CREDENTIALS_DIR") or str(
        paths_raw.get("credentials", "credentials")
    )
    client_secrets = os.environ.get("MANHWA_PUBLISHER_CLIENT_SECRETS") or str(
        paths_raw.get("client_secrets_file", "client_secrets.json")
    )
    token_file = os.environ.get("MANHWA_PUBLISHER_TOKEN_FILE") or str(
        paths_raw.get("token_file", "token.json")
    )

    cfg = AppConfig(
        base_dir=base_dir,
        youtube=youtube_cfg,
        upload=upload_cfg,
        timezone=str(raw.get("timezone", "Africa/Tunis")),
        database=DatabaseConfig(path=db_path),
        paths=PathsConfig(
            logs=str(paths_raw.get("logs", "logs")),
            credentials=creds_dir,
            client_secrets_file=client_secrets,
            token_file=token_file,
        ),
        safety=SafetyConfig(
            require_approval=bool(safety_raw.get("require_approval", True)),
            allow_publication=bool(safety_raw.get("allow_publication", True)),
        ),
    )
    # Validate timezone eagerly
    _ = cfg.zone_info
    return cfg
