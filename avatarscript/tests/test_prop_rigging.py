"""Unit tests verifying the interactive prop and item rigging system."""
import pytest
from avatarscript.compiler.compiler import AvatarCompiler
from avatarscript.compiler.validator import AvatarValidationException


def test_hold_prop_compilation_and_timeline():
    code = """
scene "Prop Showcase":
    canvas 1920x1080
    fps 30
    duration 3.0s

    avatar "Player":
        character "default"
        position center
        hold item:"microphone" hand:right

        at 0.0s:
            expression happy

        at 1.0s:
            right_arm -45 duration 0.3s
            hold item:"sword" hand:left

        at 2.0s:
            hold item:"none" hand:right
"""
    compiler = AvatarCompiler()
    scene = compiler.compile_source(code)
    timeline = scene.avatars["Player"]

    # Initial state (t=0.5s): right hand holds microphone, left has none
    s0 = timeline.evaluate_at(0.5)
    layer_names = [l.name for l in s0.layers]
    assert "prop_right" in layer_names
    assert "prop_left" not in layer_names
    prop_r = next(l for l in s0.layers if l.name == "prop_right")
    assert prop_r.asset_filename == "microphone.svg"

    # Mid state (t=1.5s): right hand holds microphone, left holds sword
    s1 = timeline.evaluate_at(1.5)
    layer_names_1 = [l.name for l in s1.layers]
    assert "prop_right" in layer_names_1
    assert "prop_left" in layer_names_1
    prop_l = next(l for l in s1.layers if l.name == "prop_left")
    assert prop_l.asset_filename == "sword.svg"

    # End state (t=2.5s): right hand released prop (none), left still holds sword
    s2 = timeline.evaluate_at(2.5)
    layer_names_2 = [l.name for l in s2.layers]
    assert "prop_right" not in layer_names_2
    assert "prop_left" in layer_names_2


def test_hold_invalid_prop_detected_by_validator():
    code = """
scene "Bad Prop":
    canvas 1920x1080
    fps 30
    duration 1.0s

    avatar "Player":
        character "default"
        hold item:"non_existent_laser_gun" hand:right
"""
    compiler = AvatarCompiler()
    with pytest.raises(AvatarValidationException) as excinfo:
        compiler.compile_source(code)
    assert "non_existent_laser_gun" in str(excinfo.value)
