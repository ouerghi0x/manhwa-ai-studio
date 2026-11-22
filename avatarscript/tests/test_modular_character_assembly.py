"""Unit tests verifying the 2D modular character assembly, anchor points, and strict Z-index hierarchy."""
from pathlib import Path
import pytest
from avatarscript.compiler.compiler import AvatarCompiler
from avatarscript.renderer.frame_renderer import FrameRenderer
from avatarscript.runtime.avatar import get_character_rig_config, CHARACTER_RIG_CONFIGS


def test_shared_anchor_coordinates():
    """Verify shared canonical anchor coordinates for modular characters."""
    cfg_jin = get_character_rig_config("jin")
    cfg_med = get_character_rig_config("medazizwerghi")

    # Shared anchor points must match exactly to avoid drift
    assert cfg_jin.head_anchor == (200.0, 140.0)
    assert cfg_med.head_anchor == (200.0, 140.0)
    assert cfg_jin.neck_anchor == (200.0, 204.0)
    assert cfg_med.neck_anchor == (200.0, 204.0)
    assert cfg_jin.shoulder_left == (130.0, 215.0)
    assert cfg_med.shoulder_left == (130.0, 215.0)
    assert cfg_jin.shoulder_right == (270.0, 215.0)
    assert cfg_med.shoulder_right == (270.0, 215.0)
    assert cfg_jin.hip_anchor == (200.0, 310.0)
    assert cfg_med.hip_anchor == (200.0, 310.0)
    assert cfg_jin.outline_stroke_width == 2.5
    assert cfg_med.outline_stroke_width == 2.5


def test_strict_z_index_hierarchy():
    """Verify that layers strictly follow the 0-11 layer hierarchy (Back to Front)."""
    code = """
scene "Hierarchy Test":
    canvas 1280x720
    fps 30
    duration 2.0s

    avatar "Jin":
        character "jin"
        position left

        at 0.0s:
            left_arm 30 duration 0.5s
            right_arm -25 duration 0.5s

    avatar "MedAziz":
        character "medazizwerghi"
        position right
"""
    compiler = AvatarCompiler()
    scene = compiler.compile_source(code)

    for avatar_name in ("Jin", "MedAziz"):
        timeline = scene.avatars[avatar_name]
        state = timeline.evaluate_at(0.2)
        layers = state.layers

        # Check that layers are strictly non-decreasing in z_order
        z_orders = [l.z_order for l in layers]
        assert z_orders == sorted(z_orders), f"Z-orders out of sequence for {avatar_name}: {z_orders}"

        layer_map = {l.name: l for l in layers}

        # 0: back_hair
        assert layer_map["back_hair"].z_order == 0.0
        # 1: jacket_back
        assert layer_map["jacket_back"].z_order == 1.0
        # 2: body (base body)
        assert layer_map["body"].z_order == 2.0
        # 3: pants / legs
        assert layer_map["left_leg"].z_order == 3.0
        assert layer_map["right_leg"].z_order == 3.1
        # 4: belt (waist accessories)
        assert layer_map["belt"].z_order == 4.0
        # 5: undershirt
        assert layer_map["undershirt"].z_order == 5.0
        # 6: head & expressions
        assert layer_map["head"].z_order == 6.0
        assert layer_map["eyes"].z_order == 6.1
        assert layer_map["mouth"].z_order == 6.2
        # 7: ear_accessory
        assert layer_map["ear_accessory"].z_order == 7.0
        # 8: front_hair
        assert layer_map["front_hair"].z_order == 8.0
        # 9: arms & hands
        assert layer_map["left_arm"].z_order == 9.0
        assert layer_map["right_arm"].z_order == 9.1
        # 10: jacket sleeves
        assert layer_map["jacket_sleeve_left"].z_order == 10.0
        assert layer_map["jacket_sleeve_right"].z_order == 10.1
        # 11: jacket front flaps
        assert layer_map["jacket_front_flaps"].z_order == 11.0

        # Verify sleeves match arm angles and pivots
        assert layer_map["jacket_sleeve_left"].rotation == layer_map["left_arm"].rotation
        assert layer_map["jacket_sleeve_left"].rotation_center == layer_map["left_arm"].rotation_center
        assert layer_map["jacket_sleeve_right"].rotation == layer_map["right_arm"].rotation
        assert layer_map["jacket_sleeve_right"].rotation_center == layer_map["right_arm"].rotation_center


def test_full_modular_rendering():
    """Verify that both modular characters render cleanly without errors."""
    code = """
scene "Render Modular Duo":
    canvas 1920x1080
    fps 30
    duration 1.0s

    avatar "Jin":
        character "jin"
        position x:600 y:600

        at 0.0s:
            left_arm 20 duration 0.2s
            expression smirk

    avatar "MedAziz":
        character "medazizwerghi"
        position x:1320 y:600

        at 0.0s:
            right_arm -30 duration 0.2s
            expression happy
            hold item:"microphone" hand:right
"""
    compiler = AvatarCompiler()
    scene = compiler.compile_source(code)
    renderer = FrameRenderer()

    img = renderer.render_frame(scene.evaluate_at(0.5), transparent=True)
    assert img.size == (1920, 1080)
    assert img.mode == "RGBA"
    bbox = img.getbbox()
    assert bbox is not None
    # Ensure substantial content was rendered
    assert bbox[2] - bbox[0] > 800
    assert bbox[3] - bbox[1] > 300
