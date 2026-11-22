"""Unit tests for OAuth 2.0 token handling and secret redaction."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from publisher.utils.logger import redact_secrets
from publisher.youtube.auth import AuthenticationError, get_valid_credentials


class TestAuthAndRedaction(unittest.TestCase):
    def test_missing_token_raises_authentication_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            token_path = Path(tmp) / "token.json"
            with self.assertRaises(AuthenticationError):
                get_valid_credentials(token_path, allow_interactive=False)

    def test_expired_token_refreshes_and_saves(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            token_path = Path(tmp) / "token.json"
            token_path.write_text("{}", encoding="utf-8")

            fake_creds = MagicMock()
            fake_creds.valid = False
            fake_creds.expired = True
            fake_creds.refresh_token = "fake_refresh_tok"
            fake_creds.to_json.return_value = '{"token": "new_tok"}'

            with patch(
                "publisher.youtube.auth.load_saved_credentials", return_value=fake_creds
            ):
                result = get_valid_credentials(token_path, allow_interactive=False)
                self.assertIs(result, fake_creds)
                fake_creds.refresh.assert_called_once()
                self.assertEqual(token_path.read_text(encoding="utf-8"), '{"token": "new_tok"}')

    def test_secret_redaction_scrubs_tokens(self) -> None:
        raw = 'Authorization: Bearer ya29.secret_token_123 "refresh_token": "1//abc_xyz"'
        redacted = redact_secrets(raw)
        self.assertNotIn("ya29.secret_token_123", redacted)
        self.assertNotIn("1//abc_xyz", redacted)
        self.assertIn("[REDACTED]", redacted)


if __name__ == "__main__":
    unittest.main()
