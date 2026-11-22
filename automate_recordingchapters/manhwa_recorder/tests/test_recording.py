"""Real FFmpeg tests (Windows + gdigrab). Skipped automatically if FFmpeg is missing."""
import shutil
import subprocess
import sys
import time

import pytest

from manhwa_recorder.core.recording_engine import RecordingEngine, RecordingError, RecState
from manhwa_recorder.utils import ffmpeg as ff

pytestmark = pytest.mark.skipif(sys.platform != "win32" or not shutil.which("ffmpeg"),
                                reason="needs Windows and FFmpeg on PATH")


def _probe(path):
    exe = shutil.which("ffprobe")
    out = subprocess.run([exe, "-v", "error", "-select_streams", "v:0", "-show_entries",
                          "stream=codec_name,width,height,pix_fmt:format=duration",
                          "-of", "default=nw=1", str(path)], capture_output=True, text=True).stdout
    return dict(line.split("=", 1) for line in out.strip().splitlines())


def test_command_builder():
    cmd = ff.build_capture_command("ffmpeg", ff.Path("o.mkv"), fps=30, width=1920, height=1080,
                                   crf=20, preset="fast", region=ff.Region(10, 20, 801, 601))
    s = " ".join(cmd)
    assert "-f gdigrab" in s and "-offset_x 10" in s and "-video_size 800x600" in s
    assert "-c:v libx264" in s and "-crf 20" in s and "-preset fast" in s


def _gdigrab_works() -> bool:
    r = subprocess.run([shutil.which("ffmpeg"), "-hide_banner", "-f", "gdigrab", "-video_size", "64x64",
                        "-i", "desktop", "-frames:v", "1", "-f", "null", "-"], capture_output=True)
    return r.returncode == 0


TESTSRC = ["-re", "-f", "lavfi", "-i", "testsrc2=size=400x300:rate=15"]


@pytest.mark.parametrize("source", ["testsrc", "gdigrab"])
def test_record_pause_resume_finalize(tmp_path, source):
    if source == "gdigrab" and not _gdigrab_works():
        pytest.skip("screen capture unavailable in this session (locked screen / no interactive desktop)")
    eng = RecordingEngine(ff.find_ffmpeg(), fps=15, width=640, height=360, crf=30, preset="ultrafast")
    if source == "testsrc":
        eng.input_args = TESTSRC
    eng.start(tmp_path, "clip", ff.Region(0, 0, 400, 300))
    assert eng.state == RecState.RECORDING
    with pytest.raises(RecordingError):
        eng.start(tmp_path, "clip2", None)  # no simultaneous recordings
    time.sleep(2)
    eng.pause()
    assert eng.state == RecState.PAUSED
    paused_elapsed = eng.elapsed
    time.sleep(1.5)
    assert abs(eng.elapsed - paused_elapsed) < 0.01  # clock stops while paused
    eng.resume()
    time.sleep(2)
    assert eng.size_bytes > 0
    out = eng.stop(tmp_path / "clip.mp4")
    assert eng.state == RecState.IDLE
    assert out.exists()
    assert not list(tmp_path.glob(".clip.part*"))  # segments cleaned up
    info = _probe(out)
    assert info["codec_name"] == "h264"
    assert (info["width"], info["height"]) == ("640", "360")
    assert info["pix_fmt"] == "yuv420p"
    # ~4s recorded, the 1.5s pause excluded
    assert 3.0 <= float(info["duration"]) <= 7.0


def test_ffmpeg_crash_reported(tmp_path):
    errors = []
    eng = RecordingEngine(ff.find_ffmpeg(), fps=15, width=320, height=240, preset="ultrafast",
                          on_error=errors.append)
    eng.input_args = TESTSRC
    eng.start(tmp_path, "crash", None)
    time.sleep(1)
    from manhwa_recorder.core.recording_engine import _kill_proc_tree
    _kill_proc_tree(eng._current.proc)  # simulate unexpected termination of process tree
    time.sleep(1.5)
    assert eng.state == RecState.ERROR and errors


def test_bad_input_reports_error(tmp_path):
    eng = RecordingEngine(ff.find_ffmpeg(), fps=10, width=320, height=240)
    eng.input_args = ["-f", "lavfi", "-i", "nosuchfilter"]
    with pytest.raises(RecordingError):
        eng.start(tmp_path, "bad", None)
    assert eng.state == RecState.ERROR
