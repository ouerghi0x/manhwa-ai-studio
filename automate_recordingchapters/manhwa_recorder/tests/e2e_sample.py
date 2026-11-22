"""End-to-end check (no GUI): browser + FFmpeg + scrolling on the local sample page.

Usage (from the automate_recordingchapters folder):
    .venv\\Scripts\\python manhwa_recorder\\tests\\e2e_sample.py [chrome|msedge]

Opens a real browser window and records the screen region for ~20-40 s.
Not collected by pytest (filename does not start with test_).
"""
import json
import subprocess
import shutil
import sys
import threading
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from manhwa_recorder.config.settings import AppSettings  # noqa: E402
from manhwa_recorder.core.browser_controller import BrowserController  # noqa: E402
from manhwa_recorder.core.session import RecordingSession, SessionCallbacks  # noqa: E402

SAMPLE = Path(__file__).resolve().parents[1] / "sample" / "sample_chapter.html"


def main() -> int:
    channel = next((a for a in sys.argv[1:] if not a.startswith("--")), "chrome")
    tmp = Path(tempfile.mkdtemp(prefix="manhwa_e2e_"))
    s = AppSettings()
    s.project.series_name = "Sample Series"
    s.project.chapter_number = 1
    s.project.chapter_url = SAMPLE.as_uri()
    s.project.output_dir = str(tmp / "output")
    s.recording.width, s.recording.height, s.recording.fps = 1280, 720, 30
    s.recording.preset = "ultrafast"
    s.scroll.delay, s.scroll.profile, s.scroll.initial_delay = 0.6, "Custom", 1.0
    s.scroll.end_hold, s.scroll.end_confirmations = 1.0, 2
    s.browser.channel = channel
    s.browser.profile_dir = str(tmp / "profile")

    browser = BrowserController()
    browser.launch(channel=channel, profile_dir=s.browser.profile_dir, width=1100, height=900)
    info = browser.open(s.project.chapter_url, "auto", 10)
    print("opened:", info, "adapter:", browser.adapter.name)
    print("region:", browser.content_region())

    done = threading.Event()
    result = {}
    states = []
    cb = SessionCallbacks(on_state=states.append,
                          on_done=lambda r: (result.update(r), done.set()))
    sess = RecordingSession(s, browser, cb)
    if "--testsrc" in sys.argv:
        print("NOTE: using FFmpeg testsrc instead of screen capture")
        sess.input_args_override = ["-re", "-f", "lavfi", "-i", "testsrc2=size=1100x900:rate=30"]
    sess.start()
    # exercise pause/resume mid-way
    threading.Timer(4, sess.pause).start()
    threading.Timer(6, sess.resume).start()
    ok = done.wait(180)
    final_state = browser.scroll_state()
    browser.close()
    print("states:", states)
    print("result:", result)
    assert ok and result["ok"], result
    video = Path(result["video"])
    meta = json.loads((video.parent / "metadata.json").read_text())
    print("metadata:", json.dumps(meta, indent=1))
    assert meta["scroll_count"] > 5
    assert "end of chapter" in result["reason"], result["reason"]
    assert final_state["y"] + final_state["vh"] >= final_state["h"] - 4
    out = subprocess.run([shutil.which("ffprobe"), "-v", "error", "-show_entries",
                          "stream=codec_name,width,height:format=duration", "-of", "default=nw=1",
                          str(video)], capture_output=True, text=True).stdout
    print(out)
    assert "codec_name=h264" in out and "width=1280" in out
    print("E2E OK:", video)
    return 0


if __name__ == "__main__":
    sys.exit(main())
