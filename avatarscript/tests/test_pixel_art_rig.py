"""Tests for 16-bit retro pixel art character rigs and nearest-neighbor rendering."""
from pathlib import Path
from PIL import Image
from avatarscript.runtime.avatar import AvatarState, build_default_layers, get_character_rig_config
from avatarscript.renderer.frame_renderer import FrameRenderer


def test_flame_emperor_rig_config():
    cfg = get_character_rig_config("flame_emperor")
    assert cfg.is_pixel_art is True
    assert cfg.hand_socket_left == (110.0, 305.0)
    assert cfg.hand_socket_right == (290.0, 305.0)


def test_flame_emperor_layer_assets_exist():
    char_dir = Path(__file__).resolve().parent.parent / "assets" / "characters" / "flame_emperor"
    assert char_dir.exists()
    required = [
        "body.png",
        "head.png",
        "left_arm.png",
        "right_arm.png",
        "eyes_open.png",
        "eyes_closed.png",
        "eyes_angry.png",
        "eyes_shocked.png",
        "mouth_neutral.png",
        "mouth_smirk.png",
        "mouth_happy.png",
        "mouth_angry.png",
    ]
    for layer_name in required:
        p = char_dir / layer_name
        assert p.exists(), f"Missing required layer: {layer_name}"
        with Image.open(p) as img:
            assert img.size == (400, 500)
            assert img.mode == "RGBA"


def test_flame_emperor_render_compositing():
    assets_root = Path(__file__).resolve().parent.parent / "assets"
    renderer = FrameRenderer(assets_root=assets_root)

    for expr in ["neutral", "smirk", "angry", "shocked"]:
        layers = build_default_layers(character="flame_emperor", expression=expr)
        avatar = AvatarState(identifier="test_flame", character="flame_emperor", x=200, y=250, layers=layers)
        rig_img = renderer.render_avatar_rig(avatar)
        assert rig_img.size == (400, 500)
        assert rig_img.mode == "RGBA"


def test_pixel_narrator_rig_config_and_assets():
    cfg = get_character_rig_config("pixel_narrator")
    assert cfg.is_pixel_art is True

    cfg_streamer = get_character_rig_config("streamer")
    assert cfg_streamer.is_pixel_art is True

    char_dir = Path(__file__).resolve().parent.parent / "assets" / "characters" / "pixel_narrator"
    assert char_dir.exists()
    required = [
        "body.png",
        "head.png",
        "left_arm.png",
        "right_arm.png",
        "eyes_open.png",
        "eyes_closed.png",
        "eyes_angry.png",
        "eyes_shocked.png",
        "mouth_neutral.png",
        "mouth_happy.png",
        "mouth_angry.png",
        "mouth_shocked.png",
        "mouth_smirk.png",
    ]
    for layer_name in required:
        p = char_dir / layer_name
        assert p.exists(), f"Missing required layer: {layer_name}"
        with Image.open(p) as img:
            assert img.size == (400, 500)
            assert img.mode == "RGBA"

    prop_mic = Path(__file__).resolve().parent.parent / "assets" / "props" / "streamer_mic.png"
    assert prop_mic.exists()


def test_pixel_narrator_render_compositing():
    assets_root = Path(__file__).resolve().parent.parent / "assets"
    renderer = FrameRenderer(assets_root=assets_root)

    for expr in ["neutral", "happy", "angry", "shocked", "smirk"]:
        layers = build_default_layers(character="pixel_narrator", expression=expr)
        avatar = AvatarState(identifier="test_narrator", character="pixel_narrator", x=200, y=250, layers=layers)
        rig_img = renderer.render_avatar_rig(avatar)
        assert rig_img.size == (400, 500)
        assert rig_img.mode == "RGBA"

