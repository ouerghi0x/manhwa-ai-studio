"""Tests for the dynamic explode & reassemble character animation."""
import pytest
from avatarscript.compiler.compiler import AvatarCompiler


def test_explode_dsl_parsing_and_compilation():
    script = '''scene "explode_test":
    canvas 1920x1080
    duration 5s

    avatar "narrator":
        character "flame_emperor"
        position center

        at 0.0s:
            explode duration 3.0s separated: 1.2s reassemble: 1.0s scatter: 0.5s intensity: 1.2
'''
    compiler = AvatarCompiler()
    scene = compiler.compile_source(script)
    avatar_tl = scene.avatars["narrator"]
    assert len(avatar_tl.animations) == 1
    anim = avatar_tl.animations[0]

    assert anim.kind == "explode"
    assert pytest.approx(anim.duration, 0.01) == 3.0
    assert pytest.approx(anim.hold_duration, 0.01) == 1.2
    assert pytest.approx(anim.reassemble_duration, 0.01) == 1.0
    assert pytest.approx(anim.scatter_duration, 0.01) == 0.5
    assert pytest.approx(anim.intensity, 0.01) == 1.2


def test_explode_aliases_hold_and_return():
    script = '''scene "explode_aliases":
    canvas 1920x1080
    duration 6s

    avatar "hero":
        character "flame_emperor"
        position center

        at 1.0s:
            explode duration 4.0s hold: 1.5s return: 1.2s burst: 0.6s
'''
    compiler = AvatarCompiler()
    scene = compiler.compile_source(script)
    anim = scene.avatars["hero"].animations[0]
    assert anim.kind == "explode"
    assert pytest.approx(anim.start_time, 0.01) == 1.0
    assert pytest.approx(anim.duration, 0.01) == 4.0
    assert pytest.approx(anim.hold_duration, 0.01) == 1.5
    assert pytest.approx(anim.reassemble_duration, 0.01) == 1.2
    assert pytest.approx(anim.scatter_duration, 0.01) == 0.6


def test_explode_sequence_phases_and_exact_reassembly():
    script = '''scene "explode_sequence":
    canvas 1920x1080
    duration 6s

    avatar "hero":
        character "flame_emperor"
        position center

        at 0.0s:
            expression neutral

        at 1.0s:
            explode duration 3.0s scatter: 0.5s separated: 1.0s reassemble: 1.5s
'''
    compiler = AvatarCompiler()
    scene = compiler.compile_source(script)
    tl = scene.avatars["hero"]

    # 1. Before explosion (t = 0.5s): Normal idle state
    state_idle = tl.evaluate_at(0.5)
    assert state_idle.expression == "neutral"
    idle_head = next(l for l in state_idle.layers if l.name == "head")
    idle_left_arm = next(l for l in state_idle.layers if l.name == "left_arm")
    idle_right_arm = next(l for l in state_idle.layers if l.name == "right_arm")
    idle_left_leg = next(l for l in state_idle.layers if l.name == "left_leg")
    idle_right_leg = next(l for l in state_idle.layers if l.name == "right_leg")

    # 2. At peak scatter (t = 1.0 + 0.5 = 1.5s): Pieces blown apart outward
    state_scatter = tl.evaluate_at(1.5)
    assert state_scatter.expression == "shocked"
    sc_head = next(l for l in state_scatter.layers if l.name == "head")
    sc_left_arm = next(l for l in state_scatter.layers if l.name == "left_arm")
    sc_right_arm = next(l for l in state_scatter.layers if l.name == "right_arm")
    sc_left_leg = next(l for l in state_scatter.layers if l.name == "left_leg")
    sc_right_leg = next(l for l in state_scatter.layers if l.name == "right_leg")

    # Head blown up
    assert sc_head.y < idle_head.y - 100.0
    # Left arm blown left
    assert sc_left_arm.x < idle_left_arm.x - 100.0
    # Right arm blown right
    assert sc_right_arm.x > idle_right_arm.x + 100.0
    # Left leg blown down and left
    assert sc_left_leg.x < idle_left_leg.x - 50.0
    assert sc_left_leg.y > idle_left_leg.y + 70.0
    # Right leg blown down and right
    assert sc_right_leg.x > idle_right_leg.x + 50.0
    assert sc_right_leg.y > idle_right_leg.y + 70.0

    # 3. Floating phase (t = 2.0s): Pieces hover and float separated in air
    state_float1 = tl.evaluate_at(1.8)
    state_float2 = tl.evaluate_at(2.2)
    fl1_head = next(l for l in state_float1.layers if l.name == "head")
    fl2_head = next(l for l in state_float2.layers if l.name == "head")
    assert fl1_head.y < idle_head.y - 100.0
    assert fl2_head.y < idle_head.y - 100.0
    # Floating motion produces subtle drift
    assert fl1_head.y != fl2_head.y

    # 4. Mid-reassembly (t = 1.0 + 0.5 + 1.0 + 0.75 = 3.25s): Pieces returning
    state_mid_re = tl.evaluate_at(3.25)
    mid_head = next(l for l in state_mid_re.layers if l.name == "head")
    mid_left_arm = next(l for l in state_mid_re.layers if l.name == "left_arm")
    # Distance to idle is significantly less than at peak scatter
    assert abs(mid_head.y - idle_head.y) < abs(sc_head.y - idle_head.y)
    assert abs(mid_left_arm.x - idle_left_arm.x) < abs(sc_left_arm.x - idle_left_arm.x)

    # 5. Full completion (t = 4.0s, and t = 4.5s): Perfectly reassembled to initial idle state
    state_completed = tl.evaluate_at(4.0)
    assert state_completed.expression == "neutral"
    comp_head = next(l for l in state_completed.layers if l.name == "head")
    comp_left_arm = next(l for l in state_completed.layers if l.name == "left_arm")
    comp_right_arm = next(l for l in state_completed.layers if l.name == "right_arm")
    comp_left_leg = next(l for l in state_completed.layers if l.name == "left_leg")
    comp_right_leg = next(l for l in state_completed.layers if l.name == "right_leg")

    assert pytest.approx(comp_head.x, 1e-4) == idle_head.x
    assert pytest.approx(comp_head.y, 1e-4) == idle_head.y
    assert pytest.approx(comp_head.rotation, 1e-4) == idle_head.rotation

    assert pytest.approx(comp_left_arm.x, 1e-4) == idle_left_arm.x
    assert pytest.approx(comp_left_arm.y, 1e-4) == idle_left_arm.y
    assert pytest.approx(comp_left_arm.rotation, 1e-4) == idle_left_arm.rotation

    assert pytest.approx(comp_right_arm.x, 1e-4) == idle_right_arm.x
    assert pytest.approx(comp_right_arm.y, 1e-4) == idle_right_arm.y
    assert pytest.approx(comp_right_arm.rotation, 1e-4) == idle_right_arm.rotation

    assert pytest.approx(comp_left_leg.x, 1e-4) == idle_left_leg.x
    assert pytest.approx(comp_left_leg.y, 1e-4) == idle_left_leg.y
    assert pytest.approx(comp_left_leg.rotation, 1e-4) == idle_left_leg.rotation

    assert pytest.approx(comp_right_leg.x, 1e-4) == idle_right_leg.x
    assert pytest.approx(comp_right_leg.y, 1e-4) == idle_right_leg.y
    assert pytest.approx(comp_right_leg.rotation, 1e-4) == idle_right_leg.rotation


def test_explode_fire_effect_and_rendering():
    from avatarscript.renderer.explosion_renderer import ExplosionRenderer, ExplosionState
    from avatarscript.renderer.frame_renderer import FrameRenderer
    import numpy as np

    script = '''scene "explode_fire_test":
    canvas 1920x1080
    duration 5s

    avatar "hero":
        character "flame_emperor"
        position center

        at 1.0s:
            explode duration 3.0s scatter: 0.5s separated: 1.0s reassemble: 1.5s fire: true color: "orange"
'''
    compiler = AvatarCompiler()
    scene = compiler.compile_source(script)
    tl = scene.avatars["hero"]

    # 1. State at detonation (t = 1.2s -> tau = 0.2s, mid-Phase 1 blast)
    state_det = tl.evaluate_at(1.2)
    assert state_det.explosion is not None
    assert state_det.explosion.active is True
    assert state_det.explosion.fire is True
    assert state_det.explosion.color == "orange"
    assert pytest.approx(state_det.explosion.tau, 1e-4) == 0.2

    # Render explosion fire layers directly
    behind_res, front_res = ExplosionRenderer.render_explosion(
        state_det.explosion, (state_det.x, state_det.y)
    )
    assert behind_res is not None
    assert front_res is not None
    behind_img, _, _ = behind_res
    front_img, _, _ = front_res

    # Check non-empty alpha content (fire pixels rendered)
    b_alpha = np.array(behind_img.split()[3])
    f_alpha = np.array(front_img.split()[3])
    assert np.max(b_alpha) > 100, "Behind fire layer is empty!"
    assert np.max(f_alpha) > 100, "Front fire sparks layer is empty!"

    # Render full composite frame at peak explosion
    frame_renderer = FrameRenderer(compiler.validator.assets_root)
    scene_state = scene.evaluate_at(1.2)
    frame = frame_renderer.render_frame(scene_state)
    assert frame.size == (1920, 1080)
    frame_arr = np.array(frame)
    # Check that fire brightness is present in the frame
    assert np.max(frame_arr[..., 0]) > 200  # High red channel in fire blast

    # 2. State at completion (t = 4.1s -> explosion finished)
    state_done = tl.evaluate_at(4.1)
    assert state_done.explosion is None
    b_done, f_done = ExplosionRenderer.render_explosion(
        ExplosionState(active=False), (state_done.x, state_done.y)
    )
    assert b_done is None
    assert f_done is None
