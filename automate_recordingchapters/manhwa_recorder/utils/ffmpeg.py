"""FFmpeg discovery, capability probing and command building."""
from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


class FFmpegNotFound(RuntimeError):
    pass


@dataclass
class Region:
    x: int
    y: int
    w: int
    h: int

    def normalized(self) -> "Region":
        """Normalize coordinates and clamp within the Windows virtual desktop bounds."""
        import sys
        nx, ny, nw, nh = self.x, self.y, self.w, self.h
        if sys.platform == "win32":
            try:
                import ctypes
                try:
                    ctypes.windll.shcore.SetProcessDpiAwareness(2)
                except Exception:
                    pass
                u = ctypes.windll.user32
                vx = u.GetSystemMetrics(76)  # SM_XVIRTUALSCREEN
                vy = u.GetSystemMetrics(77)  # SM_YVIRTUALSCREEN
                vw = u.GetSystemMetrics(78)  # SM_CXVIRTUALSCREEN
                vh = u.GetSystemMetrics(79)  # SM_CYVIRTUALSCREEN
                if vw > 0 and vh > 0:
                    nx = max(vx, min(nx, vx + vw - 16))
                    ny = max(vy, min(ny, vy + vh - 16))
                    nw = max(16, min(nw, vx + vw - nx))
                    nh = max(16, min(nh, vy + vh - ny))
            except Exception:
                pass
        # gdigrab needs positive even sizes for libx264 safety
        nw = max(16, nw - nw % 2)
        nh = max(16, nh - nh % 2)
        return Region(nx, ny, nw, nh)


@dataclass
class FFmpegCaps:
    path: str
    version: str
    gdigrab: bool
    libx264: bool


def resolve_real_binary(path_str: str) -> str:
    """Resolve Chocolatey/Scoop shims to the real underlying binary if present."""
    p = Path(path_str)
    # Check Chocolatey lib directory pattern
    if "chocolatey" in path_str.lower() and "bin" in path_str.lower():
        real_cand = Path(r"C:\ProgramData\chocolatey\lib\ffmpeg\tools\ffmpeg\bin") / p.name
        if real_cand.is_file():
            return str(real_cand)
    return path_str


def find_ffmpeg(configured: str = "") -> str:
    if configured:
        p = Path(configured)
        if p.is_file():
            return resolve_real_binary(str(p))
        raise FFmpegNotFound(f"Configured FFmpeg not found: {configured}")
    found = shutil.which("ffmpeg")
    if not found:
        raise FFmpegNotFound("FFmpeg was not found on PATH. Install it (see README) "
                             "or set its path in Settings.")
    return resolve_real_binary(found)


def _run(args: list[str]) -> str:
    r = subprocess.run(args, capture_output=True, text=True, timeout=20,
                       creationflags=CREATE_NO_WINDOW, encoding="utf-8", errors="replace")
    return r.stdout + r.stderr


def probe(configured: str = "") -> FFmpegCaps:
    path = find_ffmpeg(configured)
    version = _run([path, "-hide_banner", "-version"]).splitlines()[0:1]
    devices = _run([path, "-hide_banner", "-devices"])
    encoders = _run([path, "-hide_banner", "-encoders"])
    return FFmpegCaps(path=path, version=version[0] if version else "unknown",
                      gdigrab="gdigrab" in devices, libx264="libx264" in encoders)


def build_capture_command(ffmpeg: str, output: Path, *, fps: int, width: int, height: int,
                          crf: int, preset: str, region: Region | None,
                          draw_mouse: bool = False, input_args: list[str] | None = None) -> list[str]:
    """gdigrab capture of the desktop (or a region) scaled/padded to width x height.

    input_args replaces the gdigrab input (used by tests, e.g. a lavfi testsrc)."""
    cmd = [ffmpeg, "-hide_banner", "-y", "-loglevel", "info", "-stats"]
    if input_args:
        cmd += input_args
    else:
        cmd += ["-f", "gdigrab", "-framerate", str(fps), "-draw_mouse", "1" if draw_mouse else "0"]
        if region is not None:
            r = region.normalized()
            cmd += ["-offset_x", str(r.x), "-offset_y", str(r.y), "-video_size", f"{r.w}x{r.h}"]
        cmd += ["-i", "desktop"]
    vf = (f"scale={width}:{height}:force_original_aspect_ratio=decrease:flags=lanczos,"
          f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=black,setsar=1,format=yuv420p")
    cmd += ["-vf", vf, "-c:v", "libx264", "-preset", preset, "-crf", str(crf),
            "-flush_packets", "1", "-r", str(fps), str(output)]
    return cmd


def build_concat_command(ffmpeg: str, list_file: Path, output: Path) -> list[str]:
    cmd = [ffmpeg, "-hide_banner", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
           "-i", str(list_file), "-c", "copy"]
    if output.suffix.lower() == ".mp4":
        cmd += ["-movflags", "+faststart"]
    return cmd + [str(output)]


def build_snapshot_command(ffmpeg: str, output: Path, region: Region | None) -> list[str]:
    cmd = [ffmpeg, "-hide_banner", "-y", "-loglevel", "error", "-f", "gdigrab", "-draw_mouse", "0"]
    if region is not None:
        r = region.normalized()
        cmd += ["-offset_x", str(r.x), "-offset_y", str(r.y), "-video_size", f"{r.w}x{r.h}"]
    return cmd + ["-i", "desktop", "-frames:v", "1", str(output)]


CAPTURE_HINT = ("Windows refused the screen capture. Make sure the PC is unlocked, no UAC prompt "
                "is open, and the app runs in your normal desktop session (not via SSH/a service).")


def explain_error(stderr_lines: list[str]) -> str:
    text = " ".join(stderr_lines)
    if "Failed to capture image" in text or "does not contain any stream" in text:
        return CAPTURE_HINT
    return ""


def concat_list_line(path: Path) -> str:
    escaped = str(path.resolve()).replace("\\", "/").replace("'", "'\\''")
    return f"file '{escaped}'\n"


def probe_duration(ffmpeg: str, media: Path) -> float | None:
    """Duration in seconds using ffprobe next to ffmpeg (if available)."""
    ffprobe = Path(ffmpeg).with_name("ffprobe.exe" if ffmpeg.lower().endswith(".exe") else "ffprobe")
    exe = str(ffprobe) if ffprobe.exists() else shutil.which("ffprobe")
    if not exe:
        return None
    out = _run([exe, "-v", "error", "-show_entries", "format=duration",
                "-of", "default=nw=1:nk=1", str(media)]).strip()
    try:
        return float(out.splitlines()[0])
    except (ValueError, IndexError):
        return None
