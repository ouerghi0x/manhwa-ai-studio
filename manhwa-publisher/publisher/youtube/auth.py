"""Google OAuth 2.0 authentication and token management for YouTube Data API v3."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

logger = logging.getLogger("publisher.youtube.auth")

YOUTUBE_SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube",
    "https://www.googleapis.com/auth/youtube.readonly",
]


class AuthenticationError(Exception):
    """Raised when OAuth credentials are missing, expired, or cannot be refreshed."""


def load_saved_credentials(token_path: Path) -> Credentials | None:
    """Load persisted OAuth 2.0 user credentials from disk if present."""
    if not token_path.exists():
        return None
    try:
        return Credentials.from_authorized_user_file(str(token_path), YOUTUBE_SCOPES)
    except Exception as exc:
        raise AuthenticationError(
            f"Failed to read OAuth token file at {token_path}. Run 'python -m publisher auth'."
        ) from exc


def save_credentials(creds: Credentials, token_path: Path) -> None:
    """Persist OAuth 2.0 user credentials safely without logging token contents."""
    token_path.parent.mkdir(parents=True, exist_ok=True)
    token_path.write_text(creds.to_json(), encoding="utf-8")
    logger.info("OAuth token saved to %s", token_path)


def authenticate_interactive(
    client_secrets_path: Path,
    token_path: Path,
    *,
    port: int = 0,
    open_browser: bool = True,
) -> Credentials:
    """Run the interactive OAuth 2.0 installed-app flow and persist the resulting token."""
    if not client_secrets_path.exists():
        raise AuthenticationError(
            f"OAuth client secrets file not found at {client_secrets_path}. "
            "Download your Desktop App OAuth JSON from Google Cloud Console and save it there."
        )

    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError as exc:
        raise AuthenticationError(
            "google-auth-oauthlib is not installed. Run: pip install google-auth-oauthlib"
        ) from exc

    logger.info("Starting Google OAuth 2.0 authorization flow...")
    flow = InstalledAppFlow.from_client_secrets_file(
        str(client_secrets_path),
        YOUTUBE_SCOPES,
    )
    creds = flow.run_local_server(
        port=port,
        open_browser=open_browser,
        access_type="offline",
        prompt="consent",
    )
    save_credentials(creds, token_path)
    return creds


def get_valid_credentials(
    token_path: Path,
    *,
    client_secrets_path: Path | None = None,
    allow_interactive: bool = False,
) -> Credentials:
    """Return valid OAuth 2.0 credentials, refreshing automatically when expired.

    Never triggers an interactive browser flow unless allow_interactive=True,
    keeping headless AI-agent CLI runs strictly non-interactive.
    """
    creds = load_saved_credentials(token_path)

    if creds is not None and creds.valid:
        return creds

    if creds is not None and creds.expired and creds.refresh_token:
        try:
            logger.info("Refreshing expired YouTube OAuth access token...")
            creds.refresh(Request())
            save_credentials(creds, token_path)
            return creds
        except RefreshError as exc:
            raise AuthenticationError(
                "Failed to refresh YouTube OAuth token (it may have been revoked). "
                "Re-authenticate with: python -m publisher auth"
            ) from exc

    if allow_interactive and client_secrets_path is not None:
        return authenticate_interactive(client_secrets_path, token_path)

    raise AuthenticationError(
        f"No valid YouTube OAuth token found at {token_path}. "
        "Run 'python -m publisher auth' once to authorize your YouTube channel."
    )


def build_youtube_service(creds: Credentials) -> Any:
    """Build an authenticated YouTube Data API v3 client (never uses API keys)."""
    return build("youtube", "v3", credentials=creds, cache_discovery=False)
