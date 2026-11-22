"""Unit tests for CLI commands, exit codes, and strict JSON output mode."""

from __future__ import annotations

import io
import json
import logging
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

from publisher.cli import main
from publisher.core.validator import VideoProbeInfo
from publisher.exit_codes import ExitCode


class TestCLI(unittest.TestCase):
    def _close_log_handlers(self) -> None:
        pub_logger = logging.getLogger("publisher")
        for h in list(pub_logger.handlers):
            pub_logger.removeHandler(h)
            h.close()

    def _run_cli(self, argv: list[str]) -> tuple[int, str, str]:
        out = io.StringIO()
        err = io.StringIO()
        try:
            with redirect_stdout(out), redirect_stderr(err):
                code = main(argv)
            return code, out.getvalue(), err.getvalue()
        finally:
            self._close_log_handlers()

    def test_validate_invalid_metadata_returns_exit_2_and_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            cfg = tmp_dir / "config.yaml"
            cfg.write_text(
                f"database:\n  path: '{tmp_dir.as_posix()}/db.sqlite'\n"
                f"paths:\n  logs: '{tmp_dir.as_posix()}/logs'\n",
                encoding="utf-8",
            )
            bad_meta = tmp_dir / "bad.json"
            bad_meta.write_text('{"description": "missing title and type"}', encoding="utf-8")
            vid = tmp_dir / "v.mp4"
            vid.write_bytes(b"data")

            code, stdout, _ = self._run_cli(
                [
                    "validate",
                    "--video",
                    str(vid),
                    "--metadata",
                    str(bad_meta),
                    "--config",
                    str(cfg),
                    "--json",
                ]
            )
            self.assertEqual(code, int(ExitCode.INVALID_INPUT))
            parsed = json.loads(stdout)
            self.assertFalse(parsed["success"])
            self.assertFalse(parsed["valid"])

    def test_publish_requires_approval_returns_exit_6(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            cfg = tmp_dir / "config.yaml"
            cfg.write_text(
                f"database:\n  path: '{tmp_dir.as_posix()}/db.sqlite'\n"
                f"paths:\n  logs: '{tmp_dir.as_posix()}/logs'\n"
                "upload:\n  file_ready_timeout_seconds: 0.1\n"
                "safety:\n  require_approval: true\n  allow_publication: true\n",
                encoding="utf-8",
            )
            meta = tmp_dir / "pub.json"
            meta.write_text(
                json.dumps({"title": "Public Ep", "type": "long", "visibility": "public"}),
                encoding="utf-8",
            )
            vid = tmp_dir / "ep.mp4"
            vid.write_bytes(b"video bytes")

            code, stdout, _ = self._run_cli(
                [
                    "publish",
                    "--video",
                    str(vid),
                    "--metadata",
                    str(meta),
                    "--config",
                    str(cfg),
                    "--json",
                ]
            )
            self.assertEqual(code, int(ExitCode.REQUIRES_APPROVAL))
            parsed = json.loads(stdout)
            self.assertFalse(parsed["success"])

    def test_status_and_queue_empty_return_exit_0_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            cfg = tmp_dir / "config.yaml"
            cfg.write_text(
                f"database:\n  path: '{tmp_dir.as_posix()}/db.sqlite'\n"
                f"paths:\n  logs: '{tmp_dir.as_posix()}/logs'\n",
                encoding="utf-8",
            )

            code_s, out_s, _ = self._run_cli(["status", "--config", str(cfg), "--json"])
            self.assertEqual(code_s, int(ExitCode.SUCCESS))
            self.assertEqual(json.loads(out_s)["count"], 0)

            code_q, out_q, _ = self._run_cli(["queue", "--config", str(cfg), "--json"])
            self.assertEqual(code_q, int(ExitCode.SUCCESS))
            self.assertEqual(json.loads(out_q)["count"], 0)

    def test_validate_valid_video_returns_exit_0(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            cfg = tmp_dir / "config.yaml"
            cfg.write_text(
                f"database:\n  path: '{tmp_dir.as_posix()}/db.sqlite'\n"
                f"paths:\n  logs: '{tmp_dir.as_posix()}/logs'\n",
                encoding="utf-8",
            )
            meta = tmp_dir / "ok.json"
            meta.write_text(json.dumps({"title": "OK", "type": "long"}), encoding="utf-8")
            vid = tmp_dir / "ok.mp4"
            vid.write_bytes(b"video")

            fake_probe = VideoProbeInfo(
                file_size_bytes=5,
                duration_seconds=30.0,
                width=1920,
                height=1080,
                video_codec="h264",
                audio_codec="aac",
                has_audio=True,
                format_name="mp4",
            )
            with patch("publisher.core.validator.probe_video", return_value=fake_probe):
                code, stdout, _ = self._run_cli(
                    [
                        "validate",
                        "--video",
                        str(vid),
                        "--metadata",
                        str(meta),
                        "--config",
                        str(cfg),
                        "--json",
                    ]
                )
            self.assertEqual(code, int(ExitCode.SUCCESS))
            self.assertTrue(json.loads(stdout)["valid"])


if __name__ == "__main__":
    unittest.main()
