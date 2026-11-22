"""Phase 1 unit tests: deterministic state evaluation, SVG layer rendering, and transforms."""
from pathlib import Path
import pytest
from avatarscript.runtime.scene import Scene
from avatarscript.runtime.animation import (
    AvatarTimeline,
    AnimationEvent,
    ExpressionEvent,
    IdleConfig,
)
from avatarscript.renderer.frame_renderer import FrameRenderer


def test_deterministic_positions_at_0_1_2_3_seconds():
    """Verify exact deterministic positions at t=0, 1, 2, and 3 seconds regardless of evaluation order."""
    timeline = AvatarTimeline(
        identifier="hero",
        character="default",
        initial_x=100.0,
        initial_y=500.0,
        initial_scale=1.0,
        initial_rotation=0.0,
        idle=IdleConfig(breathe=False, blink_interval=None),
        expressions=[
            ExpressionEvent(timestamp=0.0, expression="neutral"),
            ExpressionEvent(timestamp=1.0, expression="surprised"),
            ExpressionEvent(timestamp=2.0, expression="happy"),
            ExpressionEvent(timestamp=3.0, expression="angry"),
        ],
        animations=[
            AnimationEvent(
                kind="move",
                start_time=0.0,
                duration=2.0,
                easing="linear",
                target_x=300.0,
                target_y=500.0,
            ),
            AnimationEvent(
                kind="scale",
                start_time=1.0,
                duration=2.0,
                easing="linear",
                target_scale=1.5,
            ),
            AnimationEvent(
                kind="rotate",
                start_time=2.0,
                duration=1.0,
                easing="linear",
                target_rotation=15.0,
            ),
        ],
    )
    scene = Scene(name="test_scene", avatars={"hero": timeline})

    # Evaluate out of order (t=3, t=1, t=0, t=2) to prove frame-independence
    s3 = scene.evaluate_at(3.0).avatars[0]
    s1 = scene.evaluate_at(1.0).avatars[0]
    s0 = scene.evaluate_at(0.0).avatars[0]
    s2 = scene.evaluate_at(2.0).avatars[0]

    assert s0.x == pytest.approx(100.0)
    assert s0.scale == pytest.approx(1.0)
    assert s0.rotation == pytest.approx(0.0)
    assert s0.expression == "neutral"

    assert s1.x == pytest.approx(200.0)
    assert s1.scale == pytest.approx(1.0)
    assert s1.rotation == pytest.approx(0.0)
    assert s1.expression == "surprised"

    assert s2.x == pytest.approx(300.0)
    assert s2.scale == pytest.approx(1.25)
    assert s2.rotation == pytest.approx(0.0)
    assert s2.expression == "happy"

    assert s3.x == pytest.approx(300.0)
    assert s3.scale == pytest.approx(1.5)
    assert s3.rotation == pytest.approx(15.0)
    assert s3.expression == "angry"


def test_svg_layer_compositing_and_frame_render():
    """Verify that all 6 SVG layers rasterize cleanly and composite into a non-empty RGBA frame."""
    from examples.phase1_demo import create_phase1_demo_scene

    scene = create_phase1_demo_scene()
    renderer = FrameRenderer()

    for t in (0.0, 1.0, 2.0, 3.0):
        state = scene.evaluate_at(t)
        img = renderer.render_frame(state, transparent=True)
        assert img.size == (1920, 1080)
        assert img.mode == "RGBA"
        # Ensure avatar pixels are rendered (bounding box of non-zero alpha is non-empty)
        bbox = img.getbbox()
        assert bbox is not None
        assert (bbox[2] - bbox[0]) > 200
        assert (bbox[3] - bbox[1]) > 250
