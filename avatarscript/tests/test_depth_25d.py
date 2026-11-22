"""Tests for 2.5D pseudo-3D head turn and eye tracking parallax."""
import textwrap
from avatarscript.compiler.compiler import AvatarCompiler


def test_parse_and_compile_head_turn_and_look():
    script = textwrap.dedent("""
    scene "Depth25D":
        canvas 1920x1080
        fps 30
        duration 3.0s

        avatar "hero":
            character "default"
            position center

            at 0.0s:
                expression neutral

            at 0.5s:
                head_turn yaw:30 pitch:-10 duration 0.5s easing ease_out
                look at:left duration 0.2s

            at 1.5s:
                head_turn yaw:-30 pitch:15 duration 0.5s easing ease_in_out
                look at:right duration 0.3s
    """).strip()
    compiler = AvatarCompiler()
    scene = compiler.compile_source(script)
    assert "hero" in scene.avatars
    timeline = scene.avatars["hero"]

    assert len(timeline.head_turn_events) == 2
    assert timeline.head_turn_events[0].yaw == 30.0
    assert timeline.head_turn_events[0].pitch == -10.0
    assert timeline.head_turn_events[0].duration == 0.5

    assert len(timeline.look_events) == 2
    assert timeline.look_events[0].target == "left"
    assert timeline.look_events[1].target == "right"


def test_depth_parallax_differential_evaluation():
    script = textwrap.dedent("""
    scene "ParallaxTest":
        canvas 1920x1080
        fps 30
        duration 2.0s

        avatar "hero":
            character "default"
            position center

            at 0.0s:
                head_turn yaw:45 pitch:0 duration 0.4s
                look at:right duration 0.2s
    """).strip()
    compiler = AvatarCompiler()
    scene = compiler.compile_source(script)
    timeline = scene.avatars["hero"]

    # At t=0.0s, yaw is 0
    state_0 = timeline.evaluate_at(0.0)
    layer_map_0 = {l.name: l for l in state_0.layers}
    assert layer_map_0["head"].x == 0.0
    
    # At t=0.5s (after 0.4s duration), yaw is 45 degrees, look is right
    state_turned = timeline.evaluate_at(0.5)
    layer_map_turned = {l.name: l for l in state_turned.layers}

    # Verify parallax depth principle:
    # Foreground features (eyes, mouth) MUST shift more horizontally than the head base
    head_x = layer_map_turned["head"].x
    eyes_x = layer_map_turned["eyes"].x
    mouth_x = layer_map_turned["mouth"].x

    assert head_x > 0.0
    assert mouth_x > head_x, f"Mouth ({mouth_x}) should shift more than Head ({head_x})"
    assert eyes_x > mouth_x, f"Eyes ({eyes_x}) should shift more than Mouth ({mouth_x})"

    # Verify perspective compression:
    # Eyes scale_x should compress below 1.0 when head is turned 45 degrees
    assert layer_map_turned["eyes"].scale_x < 1.0
    assert layer_map_turned["mouth"].scale_x < 1.0
