"""Video and transparent PNG sequence exporter for AvatarScript."""
import shutil
import subprocess
from pathlib import Path
from typing import List, Optional
from avatarscript.runtime.scene import Scene
from avatarscript.runtime.timeline import iter_scene_frames
from avatarscript.renderer.frame_renderer import FrameRenderer


def _resolve_ffmpeg_exe() -> str:
    """Resolve the system ffmpeg binary or fall back to imageio_ffmpeg's bundled binary."""
    sys_ffmpeg = shutil.which("ffmpeg")
    if sys_ffmpeg:
        return sys_ffmpeg
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError as exc:
        raise RuntimeError(
            "FFmpeg executable not found on PATH and imageio_ffmpeg is not installed."
        ) from exc


class VideoExporter:
    """Exports a compiled Scene to H.264 MP4 video or a transparent PNG frame sequence."""

    def __init__(self, renderer: Optional[FrameRenderer] = None):
        self.renderer = renderer or FrameRenderer()

    def export_png_sequence(
        self,
        scene: Scene,
        output_dir: Path,
        transparent: bool = True,
        prefix: str = "frame_",
    ) -> List[Path]:
        """Render all frames in the scene as a numbered PNG sequence (supports full RGBA alpha)."""
        out_dir = Path(output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        written_files: List[Path] = []

        for frame_idx, _t, state in iter_scene_frames(scene):
            img = self.renderer.render_frame(state, transparent=transparent)
            frame_path = out_dir / f"{prefix}{frame_idx:05d}.png"
            img.save(frame_path, format="PNG")
            written_files.append(frame_path)

        return written_files

    def export_mp4(
        self,
        scene: Scene,
        output_path: Optional[Path] = None,
        preset: str = "fast",
        crf: int = 18,
    ) -> Path:
        """Render the scene directly into an H.264 MP4 video (yuv420p) via FFmpeg stdin pipe."""
        if output_path is None:
            target_str = scene.output_path or f"{scene.name}.mp4"
            output_path = Path(target_str)
        else:
            output_path = Path(output_path)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        ffmpeg_exe = _resolve_ffmpeg_exe()

        cmd = [
            ffmpeg_exe,
            "-y",
            "-f",
            "rawvideo",
            "-vcodec",
            "rawvideo",
            "-s",
            f"{scene.width}x{scene.height}",
            "-pix_fmt",
            "rgb24",
            "-r",
            str(scene.fps),
            "-i",
            "-",
            "-c:v",
            "libx264",
            "-preset",
            preset,
            "-crf",
            str(crf),
            "-pix_fmt",
            "yuv420p",
            str(output_path),
        ]

        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        assert proc.stdin is not None

        try:
            for _frame_idx, _t, state in iter_scene_frames(scene):
                rgba_img = self.renderer.render_frame(state, transparent=False)
                rgb_img = rgba_img.convert("RGB")
                proc.stdin.write(rgb_img.tobytes())
        finally:
            proc.stdin.close()

        _stdout, stderr = proc.communicate()
        if proc.returncode != 0:
            err_msg = stderr.decode("utf-8", errors="replace")
            raise RuntimeError(f"FFmpeg MP4 export failed (exit {proc.returncode}):\n{err_msg}")

        return output_path
