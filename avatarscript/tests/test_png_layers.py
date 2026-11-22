"""Unit tests verifying RGBA PNG character and prop layer support."""
from pathlib import Path
from PIL import Image, ImageDraw
import pytest

from avatarscript.compiler.compiler import AvatarCompiler
from avatarscript.renderer.frame_renderer import FrameRenderer, SVGRasterizer


def _create_rgba_png(path: Path, size: tuple[int, int], box: tuple[int, int, int, int], color: tuple[int, int, int, int]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.rectangle(box, fill=color)
    img.save(path, format="PNG")


def test_png_character_layers_and_expression_fallback(tmp_path: Path):
    """Verify full PNG character compilation, fallback expressions, and compositing."""
    assets_root = tmp_path / "assets"
    char_dir = assets_root / "characters" / "brick_host"

    # High-res 800x1000 body/head (2x of 400x500) + square 512x512 mouth to test aspect-safe fitting
    _create_rgba_png(char_dir / "body.png", (800, 1000), (200, 440, 600, 920), (200, 40, 40, 255))
    _create_rgba_png(char_dir / "left_arm.png", (400, 500), (60, 250, 110, 360), (220, 180, 40, 255))
    _create_rgba_png(char_dir / "right_arm.png", (400, 500), (290, 250, 340, 360), (220, 180, 40, 255))
    _create_rgba_png(char_dir / "head.png", (800, 1000), (240, 120, 560, 440), (255, 210, 50, 255))
    _create_rgba_png(char_dir / "eyes_open.png", (400, 500), (155, 130, 245, 155), (20, 20, 20, 255))
    _create_rgba_png(char_dir / "mouth_neutral.png", (512, 512), (210, 220, 302, 245), (30, 30, 30, 255))
    _create_rgba_png(char_dir / "mouth_happy.png", (400, 500), (165, 180, 235, 205), (240, 240, 240, 255))

    code = """
scene "PNG Character Test":
    canvas 1280x720
    fps 30
    duration 3.0s

    avatar "Host":
        character "brick_host"
        position center

        at 0.0s:
            expression neutral
            talk duration 1.0s
            animate aura on intensity:0.8 color:gold

        at 1.5s:
            expression shocked
            head_turn yaw:20 duration 0.4s
"""
    compiler = AvatarCompiler(assets_root=assets_root)
    scene = compiler.compile_source(code)
    renderer = FrameRenderer(assets_root=assets_root)

    # Render during speech & aura (tests lip-sync mouth switching + aura on PNG rig)
    f0 = renderer.render_frame(scene.evaluate_at(0.2), transparent=True)
    assert f0.size == (1280, 720)
    assert f0.mode == "RGBA"
    assert f0.getbbox() is not None

    # Render 'shocked' expression even though eyes_shocked.png & mouth_shocked.png are omitted
    f1 = renderer.render_frame(scene.evaluate_at(2.0), transparent=True)
    assert f1.size == (1280, 720)
    assert f1.getbbox() is not None


def test_png_prop_validation_and_rendering(tmp_path: Path):
    """Verify .png props pass validation and render cleanly onto arm sockets."""
    assets_root = tmp_path / "assets"
    char_dir = assets_root / "characters" / "png_char"
    for layer in ("body", "left_arm", "right_arm", "head", "eyes_open", "mouth_neutral"):
        _create_rgba_png(char_dir / f"{layer}.png", (400, 500), (120, 120, 280, 380), (80, 120, 220, 255))
    _create_rgba_png(assets_root / "props" / "shield.png", (256, 256), (40, 20, 216, 236), (0, 200, 140, 255))

    code = """
scene "PNG Prop Test":
    canvas 1280x720
    fps 30
    duration 2.0s

    avatar "Knight":
        character "png_char"
        position center
        hold item:"shield" hand:right scale:1.2

        at 0.5s:
            hold item:"shield.png" hand:left
"""
    compiler = AvatarCompiler(assets_root=assets_root)
    scene = compiler.compile_source(code)
    renderer = FrameRenderer(assets_root=assets_root)

    frame = renderer.render_frame(scene.evaluate_at(1.0), transparent=True)
    assert frame.size == (1280, 720)
    assert frame.getbbox() is not None


def test_load_png_preserves_aspect_ratio(tmp_path: Path):
    """Verify wide PNG images are letterboxed rather than stretched into 400x500."""
    png_path = tmp_path / "wide.png"
    _create_rgba_png(png_path, (800, 200), (0, 0, 800, 200), (255, 0, 0, 255))

    fitted = SVGRasterizer.load_png(png_path, target_size=(400, 500))
    assert fitted.size == (400, 500)
    # 800x200 scales down by 0.5 to 400x100 centered vertically -> y from 200 to 300
    bbox = fitted.getbbox()
    assert bbox == (0, 200, 400, 300)


def test_mixed_svg_and_png_layers(tmp_path: Path):
    """Verify a character can mix .png layers and .svg layers cleanly."""
    assets_root = tmp_path / "assets"
    char_dir = assets_root / "characters" / "hybrid_char"
    _create_rgba_png(char_dir / "body.png", (400, 500), (140, 220, 260, 440), (40, 90, 200, 255))
    _create_rgba_png(char_dir / "head.png", (400, 500), (140, 80, 260, 200), (255, 220, 140, 255))
    for svg_name, rect in (
        ("left_arm.svg", '<rect x="80" y="250" width="35" height="95" fill="#2255cc"/>'),
        ("right_arm.svg", '<rect x="285" y="250" width="35" height="95" fill="#2255cc"/>'),
        ("eyes_open.svg", '<circle cx="180" cy="135" r="8" fill="#111111"/><circle cx="220" cy="135" r="8" fill="#111111"/>'),
        ("mouth_neutral.svg", '<rect x="180" y="165" width="40" height="8" fill="#111111"/>'),
    ):
        (char_dir / svg_name).write_text(
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 500">{rect}</svg>',
            encoding="utf-8",
        )

    code = """
scene "Hybrid Rig Test":
    canvas 1280x720
    fps 30
    duration 1.0s

    avatar "Hybrid":
        character "hybrid_char"
        position center
"""
    compiler = AvatarCompiler(assets_root=assets_root)
    scene = compiler.compile_source(code)
    renderer = FrameRenderer(assets_root=assets_root)

    frame = renderer.render_frame(scene.evaluate_at(0.0), transparent=True)
    assert frame.size == (1280, 720)
    assert frame.getbbox() is not None


def test_missing_core_layer_raises_file_not_found(tmp_path: Path):
    """Verify missing non-fallback layers still raise FileNotFoundError clearly."""
    assets_root = tmp_path / "assets"
    (assets_root / "characters" / "empty_char").mkdir(parents=True)
    rasterizer = SVGRasterizer(assets_root)

    with pytest.raises(FileNotFoundError, match="Missing layer asset"):
        rasterizer.load_layer_image("empty_char", "body.svg")


def test_leg_controls_walk_run_and_jump_with_gongja():
    """Verify leg rotations, walk/run locomotion, jump arc, and gongja PNG leg rendering."""
    code = """
scene "Locomotion Test":
    canvas 1920x1080
    fps 30
    duration 5.0s

    avatar "Gongja":
        character "gongja"
        position x:400 y:600

        at 0.0s:
            walk x:200 duration 1.0s speed:1.0

        at 1.5s:
            jump height:120 duration 0.8s

        at 2.5s:
            left_leg 28 duration 0.2s
            right_leg -22 duration 0.2s

        at 3.2s:
            left_leg 0 duration 0.1s
            right_leg 0 duration 0.1s
            run to_x:900 duration 1.0s
"""
    compiler = AvatarCompiler()
    scene = compiler.compile_source(code)
    timeline = scene.avatars["Gongja"]

    # Mid-walk: horizontal travel + opposing leg stride + arm counter-swing
    s_walk = timeline.evaluate_at(0.125)
    layers_walk = {l.name: l for l in s_walk.layers}
    assert "left_leg" in layers_walk and "right_leg" in layers_walk
    assert s_walk.x > 400.0
    assert layers_walk["left_leg"].rotation != 0.0
    assert layers_walk["left_leg"].rotation == pytest.approx(-layers_walk["right_leg"].rotation)
    assert layers_walk["left_arm"].rotation * layers_walk["left_leg"].rotation < 0.0

    # Peak jump at t = 1.9s: vertical arc lifts y by 120px and spreads legs/arms
    s_jump = timeline.evaluate_at(1.9)
    layers_jump = {l.name: l for l in s_jump.layers}
    assert s_jump.y == pytest.approx(600.0 - 120.0, abs=1.0)
    assert layers_jump["left_leg"].rotation > 20.0
    assert layers_jump["right_leg"].rotation < -20.0

    # Direct leg stance at t = 2.8s
    s_stance = timeline.evaluate_at(2.8)
    layers_stance = {l.name: l for l in s_stance.layers}
    assert layers_stance["left_leg"].rotation == pytest.approx(28.0)
    assert layers_stance["right_leg"].rotation == pytest.approx(-22.0)

    # Mid-run at t = 3.7s: forward lean tilt and moving toward x=900
    s_run = timeline.evaluate_at(3.7)
    assert s_run.rotation > 1.0
    assert s_run.x > 600.0

    # Full FrameRenderer render succeeds cleanly for gongja with legs
    renderer = FrameRenderer()
    frame = renderer.render_frame(scene.evaluate_at(1.9), transparent=True)
    assert frame.size == (1920, 1080)
    assert frame.getbbox() is not None

