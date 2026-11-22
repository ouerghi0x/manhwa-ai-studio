"""Phase 4 unit tests: VideoExporter (MP4 H.264 at 1080p/vertical 30/60fps & transparent PNG sequences) and CLI."""
from pathlib import Path
from PIL import Image
import pytest
from avatarscript.compiler.compiler import AvatarCompiler
from avatarscript.renderer.video_exporter import VideoExporter
from avatarscript.cli import main as cli_main


def test_export_transparent_png_sequence(tmp_path: Path):
    """Verify exporting a transparent RGBA PNG sequence preserves full alpha transparency."""
    script = '''scene "png_seq_test":
    canvas 1920x1080
    background "#202020"
    fps 10
    duration 0.5s

    avatar "main":
        character "default"
        position center

        at 0s:
            expression happy
'''
    compiler = AvatarCompiler()
    scene = compiler.compile_source(script)
    exporter = VideoExporter()

    frames_dir = tmp_path / "frames"
    files = exporter.export_png_sequence(scene, output_dir=frames_dir, transparent=True)
    assert len(files) == 5  # 0.5s @ 10 fps

    first_img = Image.open(files[0])
    assert first_img.mode == "RGBA"
    assert first_img.size == (1920, 1080)
    # Corner pixel (0, 0) must be completely transparent (alpha == 0)
    assert first_img.getpixel((0, 0))[3] == 0
    # Center pixel where the avatar torso/head sits must be opaque (alpha == 255)
    assert first_img.getpixel((960, 648))[3] == 255


def test_export_mp4_1080p_30fps_and_vertical_60fps(tmp_path: Path):
    """Verify H.264 MP4 export works for both 1920x1080 @ 30fps and 1080x1920 @ 60fps."""
    script_1080p = '''scene "mp4_1080p":
    canvas 1920x1080
    background "#1E293B"
    fps 30
    duration 1s

    avatar "main":
        character "default"
        position right

        at 0s:
            expression surprised
            animate bounce duration 0.5s
'''
    script_vertical_60 = '''scene "mp4_vertical":
    canvas 1080x1920
    background "#0F172A"
    fps 60
    duration 0.5s

    avatar "main":
        character "default"
        position center

        at 0s:
            expression shocked
            animate shake duration 0.4s
'''
    compiler = AvatarCompiler()
    exporter = VideoExporter()

    mp4_1 = exporter.export_mp4(compiler.compile_source(script_1080p), output_path=tmp_path / "out_1080p.mp4")
    assert mp4_1.exists()
    assert mp4_1.stat().st_size > 2000

    mp4_2 = exporter.export_mp4(compiler.compile_source(script_vertical_60), output_path=tmp_path / "out_vert60.mp4")
    assert mp4_2.exists()
    assert mp4_2.stat().st_size > 2000


def test_cli_commands_validate_render_and_export_frames(tmp_path: Path):
    """Verify CLI subcommands: validate, render --output, and export-frames --output."""
    example_ava = Path(__file__).resolve().parent.parent / "examples" / "basic_reaction.ava"

    # 1. validate
    rc_val = cli_main(["validate", str(example_ava)])
    assert rc_val == 0

    # 2. render --output
    out_mp4 = tmp_path / "cli_reaction.mp4"
    rc_ren = cli_main(["render", str(example_ava), "--output", str(out_mp4)])
    assert rc_ren == 0
    assert out_mp4.exists()
    assert out_mp4.stat().st_size > 5000

    # 3. export-frames --output
    # Use a short 0.2s script for fast CLI frame export check
    short_ava = tmp_path / "short.ava"
    short_ava.write_text(
        '''scene "short":
    canvas 1920x1080
    fps 10
    duration 0.2s
    avatar "a":
        character "default"
''',
        encoding="utf-8",
    )
    out_frames = tmp_path / "cli_frames"
    rc_exp = cli_main(["export-frames", str(short_ava), "--output", str(out_frames)])
    assert rc_exp == 0
    assert len(list(out_frames.glob("*.png"))) == 2
