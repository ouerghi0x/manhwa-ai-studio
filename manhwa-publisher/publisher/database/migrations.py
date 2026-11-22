"""Versioned SQLite schema migrations."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

MIGRATIONS: list[tuple[int, str, str]] = [
    (
        1,
        "initial_schema",
        """
        CREATE TABLE IF NOT EXISTS upload_jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            video_path TEXT NOT NULL,
            metadata_path TEXT NOT NULL,
            sha256_hash TEXT NOT NULL UNIQUE,
            youtube_video_id TEXT UNIQUE,
            video_url TEXT,
            status TEXT NOT NULL DEFAULT 'pending',
            publish_at TEXT,
            upload_progress REAL NOT NULL DEFAULT 0.0,
            resumable_uri TEXT,
            title TEXT,
            video_type TEXT,
            visibility TEXT,
            thumbnail_path TEXT,
            playlist_id TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            error_details TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_upload_jobs_status
            ON upload_jobs(status);

        CREATE INDEX IF NOT EXISTS idx_upload_jobs_video_id
            ON upload_jobs(youtube_video_id);

        CREATE TABLE IF NOT EXISTS job_operations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id INTEGER NOT NULL,
            operation_type TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            attempts INTEGER NOT NULL DEFAULT 0,
            last_error TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(job_id, operation_type),
            FOREIGN KEY(job_id) REFERENCES upload_jobs(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_job_operations_job_id
            ON job_operations(job_id);
        """,
    ),
    (
        2,
        "add_related_video_columns",
        """
        ALTER TABLE upload_jobs ADD COLUMN related_video_id TEXT;
        ALTER TABLE upload_jobs ADD COLUMN related_job_id INTEGER;
        """,
    ),
]


def run_migrations(conn: sqlite3.Connection) -> int:
    """Apply all pending schema migrations transactionally. Returns applied count."""
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            applied_at TEXT NOT NULL
        );
        """
    )
    rows = conn.execute("SELECT version FROM schema_migrations;").fetchall()
    applied_versions = {int(row[0]) for row in rows}

    applied_count = 0
    for version, name, sql in MIGRATIONS:
        if version in applied_versions:
            continue
        now = datetime.now(timezone.utc).isoformat()
        with conn:
            conn.executescript(sql)
            conn.execute(
                "INSERT INTO schema_migrations (version, name, applied_at) VALUES (?, ?, ?);",
                (version, name, now),
            )
        applied_count += 1

    return applied_count
