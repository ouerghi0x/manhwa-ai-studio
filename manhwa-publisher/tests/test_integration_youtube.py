"""Opt-in integration test against a real, explicitly authorized YouTube channel.

Never uploads public content. Disabled by default unless:
    MANHWA_PUBLISHER_RUN_INTEGRATION=1
"""

from __future__ import annotations

import os
import unittest

from publisher.config import load_config
from publisher.youtube.auth import build_youtube_service, get_valid_credentials
from publisher.youtube.videos import get_authenticated_channel


@unittest.skipUnless(
    os.environ.get("MANHWA_PUBLISHER_RUN_INTEGRATION") == "1",
    "Set MANHWA_PUBLISHER_RUN_INTEGRATION=1 to run live YouTube API integration tests.",
)
class TestYouTubeLiveIntegration(unittest.TestCase):
    def test_authenticated_channel_reachable(self) -> None:
        config = load_config()
        creds = get_valid_credentials(config.token_path, allow_interactive=False)
        yt = build_youtube_service(creds)
        channel = get_authenticated_channel(yt)
        self.assertIsNotNone(channel)
        assert channel is not None
        self.assertIn("id", channel)


if __name__ == "__main__":
    unittest.main()
