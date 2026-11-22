"""Phase 3 unit tests: Timeline scheduling, easing curves, overlapping animations, shake/bounce/fade, and idle."""
import pytest
from avatarscript.compiler.compiler import AvatarCompiler
from avatarscript.runtime.interpolation import linear, ease_in, ease_out, ease_in_out


def test_easing_functions_mathematical_properties():
    """Verify boundary values, midpoint behavior, and monotonicity of all 4 easing functions."""
    for fn in (linear, ease_in, ease_out, ease_in_out):
        assert fn(0.0) == pytest.approx(0.0)
        assert fn(1.0) == pytest.approx(1.0)
        # Monotonicity check
        samples = [fn(i / 10.0) for i in range(11)]
        assert all(samples[i] <= samples[i + 1] + 1e-9 for i in range(10))

    assert linear(0.5) == pytest.approx(0.5)
    assert ease_in(0.5) == pytest.approx(0.25)
    assert ease_out(0.5) == pytest.approx(0.75)
    assert ease_in_out(0.5) == pytest.approx(0.5)


def test_overlapping_same_property_snapshot_on_start():
    """Verify overlapping animations on the same property smoothly snapshot the value at start_time."""
    script = '''scene "overlap_test":
    canvas 1920x1080
    duration 5s

    avatar "a1":
        character "default"
        position x:100 y:500

        at 0s:
            move to_x:300 to_y:500 duration 2s easing linear

        at 1s:
            move to_x:500 to_y:500 duration 2s easing linear
'''
    compiler = AvatarCompiler()
    scene = compiler.compile_source(script)

    # At t=0s, x=100
    assert scene.evaluate_at(0.0).avatars[0].x == pytest.approx(100.0)
    # At t=1s, the first move is 50% done -> x=200. The second move starts at t=1s from x=200!
    assert scene.evaluate_at(1.0).avatars[0].x == pytest.approx(200.0)
    # At t=2s, the second move is 50% done between 200 and 500 -> x=350!
    assert scene.evaluate_at(2.0).avatars[0].x == pytest.approx(350.0)
    # At t=3s, the second move completes at x=500
    assert scene.evaluate_at(3.0).avatars[0].x == pytest.approx(500.0)


def test_simultaneous_orthogonal_animations_and_transient_shake_bounce():
    """Verify move, scale, rotate, fade, shake, and bounce work together deterministically."""
    script = '''scene "multi_anim":
    canvas 1920x1080
    duration 6s

    avatar "reactor":
        character "default"
        position center
        scale 1.0

        idle:
            breathe
            blink every 4s

        at 0s:
            expression neutral

        at 1s:
            expression surprised
            animate shake duration 0.4s intensity 20
            scale 1.5 duration 1.0s easing linear

        at 3s:
            expression happy
            animate bounce duration 0.6s intensity 25
            rotate 20 duration 1.0s easing linear

        at 4.5s:
            expression sad
            fade 0.4 duration 0.5s easing linear
'''
    compiler = AvatarCompiler()
    scene = compiler.compile_source(script)

    # Mid-shake at t=1.08s: horizontal offset is non-zero, scale is interpolating (1.04)
    s_shake = scene.evaluate_at(1.08).avatars[0]
    assert s_shake.expression == "surprised"
    assert abs(s_shake.x - 960.0) > 5.0
    assert s_shake.scale == pytest.approx(1.04, rel=1e-2)

    # After shake finishes at t=2.0s: x returns to exact center (960.0), scale is 1.5
    s_after_shake = scene.evaluate_at(2.0).avatars[0]
    assert s_after_shake.x == pytest.approx(960.0)
    assert s_after_shake.scale == pytest.approx(1.5)

    # Mid-bounce at t=3.15s: y is displaced upward (< 648.0)
    s_bounce = scene.evaluate_at(3.15).avatars[0]
    assert s_bounce.expression == "happy"
    assert s_bounce.y < 648.0 - 10.0

    # At t=3.92s (within [3.85s, 4.00s] blink window of 4.0s interval): avatar is blinking!
    s_blink = scene.evaluate_at(3.92).avatars[0]
    assert s_blink.is_blinking is True
    eyes_layer = [l for l in s_blink.layers if l.name == "eyes"][0]
    assert eyes_layer.asset_filename == "eyes_closed.svg"

    # At t=5.2s: fade to 0.4 is complete, expression is sad
    s_fade = scene.evaluate_at(5.2).avatars[0]
    assert s_fade.expression == "sad"
    assert s_fade.opacity == pytest.approx(0.4)
