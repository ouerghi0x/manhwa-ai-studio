"""Phase 1 Demonstration: Minimum Animation Engine in Python & Pygame."""
import argparse
from pathlib import Path
from avatarscript.runtime.scene import Scene
from avatarscript.runtime.animation import (
    AvatarTimeline,
    AnimationEvent,
    ExpressionEvent,
    IdleConfig,
)
from avatarscript.renderer.frame_renderer import FrameRenderer
from avatarscript.renderer.preview import run_preview


def create_phase1_demo_scene() -> Scene:
    """Create a programmatic demo scene exercising position, scale, rotation, expressions, and idle."""
    timeline = AvatarTimeline(
        identifier="main",
        character="default",
        initial_x=480.0,
        initial_y=620.0,
        initial_scale=1.1,
        initial_rotation=0.0,
        initial_expression="neutral",
        idle=IdleConfig(breathe=True, blink_interval=4.0),
        expressions=[
            ExpressionEvent(timestamp=0.0, expression="neutral"),
            ExpressionEvent(timestamp=1.0, expression="surprised"),
            ExpressionEvent(timestamp=2.0, expression="happy"),
            ExpressionEvent(timestamp=3.0, expression="shocked"),
        ],
        animations=[
            # Move from X=480 to X=1440 over 2.0 seconds (0s -> 2s), linear easing for exact deterministic check
            AnimationEvent(
                kind="move",
                start_time=0.0,
                duration=2.0,
                easing="linear",
                target_x=1440.0,
                target_y=580.0,
            ),
            # Scale from 1.1 to 1.35 between 1.0s and 3.0s
            AnimationEvent(
                kind="scale",
                start_time=1.0,
                duration=2.0,
                easing="ease_in_out",
                target_scale=1.35,
            ),
            # Rotate to 12 degrees between 2.0s and 3.0s
            AnimationEvent(
                kind="rotate",
                start_time=2.0,
                duration=1.0,
                easing="ease_out",
                target_rotation=12.0,
            ),
        ],
    )

    return Scene(
        name="phase1_demo",
        width=1920,
        height=1080,
        background="#1E293B",
        fps=30,
        duration=4.0,
        avatars={"main": timeline},
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="AvatarScript Phase 1 Demo")
    parser.add_argument(
        "--duration",
        type=float,
        default=3.0,
        help="Auto-close Pygame window after N seconds (0 for infinite interactive loop)",
    )
    parser.add_argument(
        "--export-snapshots",
        action="store_true",
        help="Export verification PNG frames at t=0s, 1s, 2s, 3s",
    )
    args = parser.parse_args()

    scene = create_phase1_demo_scene()
    renderer = FrameRenderer()

    if args.export_snapshots:
        out_dir = Path(__file__).resolve().parent / "phase1_snapshots"
        out_dir.mkdir(exist_ok=True)
        for t in (0.0, 1.0, 2.0, 3.0):
            state = scene.evaluate_at(t)
            img = renderer.render_frame(state)
            out_path = out_dir / f"frame_t{int(t)}s.png"
            img.save(out_path)
            av = state.avatars[0]
            print(
                f"Saved {out_path.name}: pos=({av.x:.1f}, {av.y:.1f}), "
                f"scale={av.scale:.2f}, rot={av.rotation:.1f}deg, expr={av.expression}"
            )

    max_sec = args.duration if args.duration > 0 else None
    run_preview(scene, renderer=renderer, max_seconds=max_sec)


if __name__ == "__main__":
    main()
