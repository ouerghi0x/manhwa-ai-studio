"""Deterministic animation evaluation and overlapping resolution for AvatarScript."""
import math
from dataclasses import dataclass, field
from typing import List, Optional, Tuple
from pathlib import Path
from avatarscript.runtime.avatar import AvatarState, build_default_layers
from avatarscript.renderer.aura_renderer import AuraState
from avatarscript.renderer.explosion_renderer import ExplosionState
from avatarscript.runtime.interpolation import apply_easing, lerp
from avatarscript.runtime.lipsync import AudioSpeechAnalyzer


@dataclass
class AnimationEvent:
    kind: str  # 'move', 'walk', 'run', 'jump', 'scale', 'rotate', 'fade', 'shake', 'bounce', 'nod', 'arm', 'leg', 'aura'
    start_time: float
    duration: float
    easing: str = "ease_in_out"
    target_x: Optional[float] = None
    target_y: Optional[float] = None
    delta_x: Optional[float] = None
    delta_y: Optional[float] = None
    target_scale: Optional[float] = None
    target_rotation: Optional[float] = None
    target_opacity: Optional[float] = None
    intensity: float = 15.0
    # Arm control parameters
    target_arm: Optional[str] = None  # 'left', 'right', 'both'
    arm_angle: Optional[float] = None
    # Leg control parameters
    target_leg: Optional[str] = None  # 'left', 'right', 'both'
    leg_angle: Optional[float] = None
    anim_speed: float = 1.0
    # Aura parameters
    aura_active: Optional[bool] = None
    aura_color: Optional[str] = None
    aura_intensity: Optional[float] = None
    aura_size: Optional[float] = None
    aura_speed: Optional[float] = None
    aura_sparks: Optional[bool] = None
    # Explode parameters
    hold_duration: Optional[float] = None
    reassemble_duration: Optional[float] = None
    scatter_duration: Optional[float] = None
    fire_enabled: bool = True
    fire_color: str = "orange"


@dataclass
class ExpressionEvent:
    timestamp: float
    expression: str


@dataclass
class HoldEvent:
    timestamp: float
    item: str
    hand: str = "right"  # 'left' or 'right'
    scale: float = 1.0


@dataclass
class TalkEvent:
    timestamp: float
    audio: Optional[str] = None
    duration: float = 1.0
    threshold: float = 0.12
    speed: float = 1.0


@dataclass
class HeadTurnEvent:
    start_time: float
    duration: float
    yaw: float = 0.0
    pitch: float = 0.0
    easing: str = "ease_in_out"


@dataclass
class LookEvent:
    start_time: float
    duration: float
    target: Optional[str] = None
    look_x: Optional[float] = None
    look_y: Optional[float] = None
    easing: str = "ease_in_out"


@dataclass
class IdleConfig:
    breathe: bool = False
    blink_interval: Optional[float] = None  # seconds, e.g. 4.0
    blink_duration: float = 0.15


def _evaluate_channel(
    t: float,
    initial_value: float,
    events: List[Tuple[float, float, str, float, bool]],
) -> float:
    """Deterministically evaluate a single scalar channel at timestamp t.

    Each event tuple is: (start_time, duration, easing, value, is_delta).
    When a new event starts at `s_i <= t`, its starting value `v_start` is the exact
    evaluated value of the channel at `t = s_i` from all prior events (snapshot-on-start).
    """
    val = float(initial_value)
    # Sort chronologically by start_time (preserving declaration order on ties)
    sorted_evs = sorted(enumerate(events), key=lambda item: (item[1][0], item[0]))

    # We maintain the resolved (v_start, v_end, start_time, duration, easing) of each event
    resolved: List[Tuple[float, float, float, float, str]] = []

    for _, (s_time, dur, easing, target_or_delta, is_delta) in sorted_evs:
        # Compute channel value right at s_time using previously resolved events
        v_at_start = _eval_resolved_at(s_time, initial_value, resolved)
        v_end = (v_at_start + target_or_delta) if is_delta else target_or_delta
        resolved.append((s_time, dur, v_at_start, v_end, easing))

    return _eval_resolved_at(t, initial_value, resolved)


def _eval_resolved_at(
    t: float,
    initial_value: float,
    resolved: List[Tuple[float, float, float, float, str]],
) -> float:
    val = float(initial_value)
    for s_time, dur, v_start, v_end, easing in resolved:
        if t < s_time - 1e-9:
            break
        if dur <= 1e-9 or t >= s_time + dur:
            val = v_end
        else:
            prog = max(0.0, min(1.0, (t - s_time) / dur))
            eased = apply_easing(prog, easing)
            val = lerp(v_start, v_end, eased)
    return val


@dataclass
class AvatarTimeline:
    identifier: str
    character: str
    initial_x: float
    initial_y: float
    initial_scale: float = 1.0
    initial_rotation: float = 0.0
    initial_opacity: float = 1.0
    initial_expression: str = "neutral"
    initial_left_prop: str = "none"
    initial_right_prop: str = "none"
    initial_left_prop_scale: float = 1.0
    initial_right_prop_scale: float = 1.0
    idle: IdleConfig = field(default_factory=IdleConfig)
    expressions: List[ExpressionEvent] = field(default_factory=list)
    hold_events: List[HoldEvent] = field(default_factory=list)
    talk_events: List[TalkEvent] = field(default_factory=list)
    head_turn_events: List[HeadTurnEvent] = field(default_factory=list)
    look_events: List[LookEvent] = field(default_factory=list)
    animations: List[AnimationEvent] = field(default_factory=list)

    def evaluate_at(self, t: float) -> AvatarState:
        """Pure function of timestamp t: computes exact AvatarState independent of frame rate or history."""
        t = max(0.0, float(t))

        # 1. Resolve expression (latest event with timestamp <= t)
        expr = self.initial_expression
        latest_expr_time = -1.0
        for ev in sorted(self.expressions, key=lambda e: e.timestamp):
            if ev.timestamp <= t + 1e-9:
                expr = ev.expression
                latest_expr_time = ev.timestamp
            else:
                break

        # Check for active explode animation
        active_explode: Optional[AnimationEvent] = None
        for anim in self.animations:
            if anim.kind == "explode" and anim.start_time <= t < anim.start_time + anim.duration:
                active_explode = anim
                break

        if active_explode is not None:
            # If no explicit expression event occurred after the explosion began, show shocked
            if latest_expr_time < active_explode.start_time:
                expr = "shocked"

        # 2. Build independent transform channels for snapshot-on-start evaluation
        x_events: List[Tuple[float, float, str, float, bool]] = []
        y_events: List[Tuple[float, float, str, float, bool]] = []
        scale_events: List[Tuple[float, float, str, float, bool]] = []
        rot_events: List[Tuple[float, float, str, float, bool]] = []
        opacity_events: List[Tuple[float, float, str, float, bool]] = []
        left_arm_events: List[Tuple[float, float, str, float, bool]] = []
        right_arm_events: List[Tuple[float, float, str, float, bool]] = []
        left_leg_events: List[Tuple[float, float, str, float, bool]] = []
        right_leg_events: List[Tuple[float, float, str, float, bool]] = []
        yaw_events: List[Tuple[float, float, str, float, bool]] = []
        pitch_events: List[Tuple[float, float, str, float, bool]] = []
        look_x_events: List[Tuple[float, float, str, float, bool]] = []
        look_y_events: List[Tuple[float, float, str, float, bool]] = []

        # Head turn events -> yaw and pitch channels
        for ht in self.head_turn_events:
            yaw_events.append((ht.start_time, ht.duration, ht.easing, ht.yaw, False))
            pitch_events.append((ht.start_time, ht.duration, ht.easing, ht.pitch, False))

        # Look events -> look_x and look_y channels
        # Target presets:
        # 'center': (0, 0), 'left': (-10, 0), 'right': (10, 0), 'up': (0, -8), 'down': (0, 8)
        target_map = {
            "center": (0.0, 0.0),
            "left": (-10.0, 0.0),
            "right": (10.0, 0.0),
            "up": (0.0, -8.0),
            "down": (0.0, 8.0),
        }
        for lk in self.look_events:
            lx = lk.look_x
            ly = lk.look_y
            if lk.target and lk.target in target_map:
                preset_x, preset_y = target_map[lk.target]
                if lx is None:
                    lx = preset_x
                if ly is None:
                    ly = preset_y
            if lx is not None:
                look_x_events.append((lk.start_time, lk.duration, lk.easing, lx, False))
            if ly is not None:
                look_y_events.append((lk.start_time, lk.duration, lk.easing, ly, False))

        for anim in self.animations:
            if anim.kind in ("move", "walk", "run", "jump"):
                if anim.delta_x is not None:
                    x_events.append((anim.start_time, anim.duration, anim.easing, anim.delta_x, True))
                elif anim.target_x is not None:
                    x_events.append((anim.start_time, anim.duration, anim.easing, anim.target_x, False))

                if anim.delta_y is not None:
                    y_events.append((anim.start_time, anim.duration, anim.easing, anim.delta_y, True))
                elif anim.target_y is not None:
                    y_events.append((anim.start_time, anim.duration, anim.easing, anim.target_y, False))

            elif anim.kind == "scale" and anim.target_scale is not None:
                scale_events.append(
                    (anim.start_time, anim.duration, anim.easing, anim.target_scale, False)
                )
            elif anim.kind == "rotate" and anim.target_rotation is not None:
                rot_events.append(
                    (anim.start_time, anim.duration, anim.easing, anim.target_rotation, False)
                )
            elif anim.kind == "fade" and anim.target_opacity is not None:
                opacity_events.append(
                    (anim.start_time, anim.duration, anim.easing, anim.target_opacity, False)
                )
            elif anim.kind in ("arm", "left_arm", "right_arm"):
                angle = anim.arm_angle if anim.arm_angle is not None else (
                    anim.target_rotation if anim.target_rotation is not None else (
                        anim.intensity if anim.intensity is not None else 0.0
                    )
                )
                target = anim.target_arm or ("left" if anim.kind == "left_arm" else "right")
                if target in ("left", "both"):
                    left_arm_events.append((anim.start_time, anim.duration, anim.easing, angle, False))
                if target in ("right", "both"):
                    right_arm_events.append((anim.start_time, anim.duration, anim.easing, angle, False))
            elif anim.kind in ("leg", "left_leg", "right_leg"):
                angle = anim.leg_angle if anim.leg_angle is not None else (
                    anim.target_rotation if anim.target_rotation is not None else (
                        anim.intensity if anim.intensity is not None else 0.0
                    )
                )
                target = anim.target_leg or ("left" if anim.kind == "left_leg" else "right")
                if target in ("left", "both"):
                    left_leg_events.append((anim.start_time, anim.duration, anim.easing, angle, False))
                if target in ("right", "both"):
                    right_leg_events.append((anim.start_time, anim.duration, anim.easing, angle, False))

        x = _evaluate_channel(t, self.initial_x, x_events)
        y = _evaluate_channel(t, self.initial_y, y_events)
        scale = _evaluate_channel(t, self.initial_scale, scale_events)
        rotation = _evaluate_channel(t, self.initial_rotation, rot_events)
        opacity = _evaluate_channel(t, self.initial_opacity, opacity_events)
        left_arm_rot = _evaluate_channel(t, 0.0, left_arm_events)
        right_arm_rot = _evaluate_channel(t, 0.0, right_arm_events)
        left_leg_rot = _evaluate_channel(t, 0.0, left_leg_events)
        right_leg_rot = _evaluate_channel(t, 0.0, right_leg_events)
        yaw = _evaluate_channel(t, 0.0, yaw_events)
        pitch = _evaluate_channel(t, 0.0, pitch_events)
        look_x = _evaluate_channel(t, 0.0, look_x_events)
        look_y = _evaluate_channel(t, 0.0, look_y_events)

        # 3. Resolve additive transient procedural effects (shake, bounce, nod, walk, run, jump) active at t
        offset_x = 0.0
        offset_y = 0.0
        offset_rot = 0.0
        for anim in self.animations:
            if anim.start_time <= t <= anim.start_time + anim.duration and anim.duration > 1e-9:
                prog = (t - anim.start_time) / anim.duration
                envelope = math.sin(math.pi * prog)
                if anim.kind == "shake":
                    # Damped horizontal oscillation (zero at start and end)
                    offset_x += anim.intensity * envelope * math.sin(prog * math.pi * 8.0)
                elif anim.kind == "bounce":
                    # Smooth vertical jump arc (zero at start and end)
                    hop = abs(math.sin(prog * math.pi * 2.0))
                    offset_y -= hop * (anim.intensity * 2.0)
                    left_leg_rot += hop * 14.0
                    right_leg_rot -= hop * 14.0
                elif anim.kind == "nod":
                    # Head nod / body tilt pitch down & up (zero at start and end)
                    offset_rot += anim.intensity * envelope * math.sin(prog * math.pi * 2.0)
                elif anim.kind == "walk":
                    cycles = max(1.0, round(anim.duration * 2.0 * anim.anim_speed))
                    phase = prog * math.pi * 2.0 * cycles
                    stride = math.sin(phase) * envelope * 28.0
                    left_leg_rot += stride
                    right_leg_rot -= stride
                    left_arm_rot -= stride * 0.55
                    right_arm_rot += stride * 0.55
                    offset_y -= abs(math.sin(phase)) * 10.0 * envelope
                elif anim.kind == "run":
                    cycles = max(1.0, round(anim.duration * 3.2 * anim.anim_speed))
                    phase = prog * math.pi * 2.0 * cycles
                    stride = math.sin(phase) * envelope * 42.0
                    left_leg_rot += stride
                    right_leg_rot -= stride
                    left_arm_rot -= stride * 0.80
                    right_arm_rot += stride * 0.80
                    offset_y -= abs(math.sin(phase)) * 18.0 * envelope
                    offset_rot += 5.0 * envelope
                elif anim.kind == "jump":
                    jump_arc = math.sin(math.pi * prog)
                    offset_y -= jump_arc * anim.intensity
                    left_leg_rot += jump_arc * 32.0
                    right_leg_rot -= jump_arc * 28.0
                    left_arm_rot += jump_arc * 35.0
                    right_arm_rot -= jump_arc * 35.0
                elif anim.kind == "explode":
                    tau = t - anim.start_time
                    s_dur = anim.scatter_duration if anim.scatter_duration is not None else 0.4
                    if tau < s_dur:
                        u = tau / max(1e-4, s_dur)
                        burst_envelope = math.sin(math.pi * u) * (1.0 - u)
                        offset_x += burst_envelope * (16.0 * anim.intensity) * math.sin(u * math.pi * 10.0)

        # 4. Resolve idle behaviors (breathing & blinking)
        breathe_offset_y = 0.0
        breathe_scale_y = 1.0
        if self.idle.breathe:
            phase = math.sin(2.0 * math.pi * t / 3.0)
            breathe_offset_y = -4.0 * phase
            breathe_scale_y = 1.0 + 0.015 * phase

        is_blinking = False
        if self.idle.blink_interval and self.idle.blink_interval > 0.2:
            cycle_pos = t % self.idle.blink_interval
            if cycle_pos >= (self.idle.blink_interval - self.idle.blink_duration):
                is_blinking = True

        # Resolve held props (latest hold events with timestamp <= t)
        left_prop = self.initial_left_prop
        right_prop = self.initial_right_prop
        left_prop_scale = self.initial_left_prop_scale
        right_prop_scale = self.initial_right_prop_scale
        for hev in sorted(self.hold_events, key=lambda h: h.timestamp):
            if hev.timestamp <= t + 1e-9:
                if hev.hand == "left":
                    left_prop = hev.item
                    left_prop_scale = hev.scale
                elif hev.hand == "right":
                    right_prop = hev.item
                    right_prop_scale = hev.scale
            else:
                break

        layers = build_default_layers(
            character=self.character,
            expression=expr,
            is_blinking=is_blinking,
            breathe_offset_y=breathe_offset_y,
            breathe_scale_y=breathe_scale_y,
            left_arm_rot=left_arm_rot,
            right_arm_rot=right_arm_rot,
            left_leg_rot=left_leg_rot,
            right_leg_rot=right_leg_rot,
            left_prop=left_prop,
            right_prop=right_prop,
            left_prop_scale=left_prop_scale,
            right_prop_scale=right_prop_scale,
            yaw=yaw,
            pitch=pitch,
            look_x=look_x,
            look_y=look_y,
        )

        # Resolve active speech/talking viseme at timestamp t
        speaking_mouth: Optional[str] = None
        for tev in self.talk_events:
            if tev.timestamp <= t <= tev.timestamp + tev.duration and tev.duration > 1e-9:
                t_offset = t - tev.timestamp
                if tev.audio:
                    audio_p = Path(tev.audio)
                    if not audio_p.is_absolute() and not audio_p.exists():
                        # Check workspace root
                        cand = Path.cwd() / tev.audio
                        if cand.exists():
                            audio_p = cand
                    speaking_mouth = AudioSpeechAnalyzer.get_mouth_at(
                        audio_p, t_offset, threshold=tev.threshold, base_expression=expr
                    )
                else:
                    # Procedural chatter animation
                    chatter_cycle = math.sin(t_offset * 16.0 * tev.speed)
                    speaking_mouth = "mouth_happy.svg" if chatter_cycle > 0 else f"mouth_{expr}.svg"
                break

        # Swap mouth layer if currently articulating speech
        if speaking_mouth:
            for l in layers:
                if l.name == "mouth":
                    l.asset_filename = speaking_mouth
                    break

        # Resolve Explode dynamic layer displacement & reassembly
        if active_explode is not None:
            tau = t - active_explode.start_time
            dur = max(1e-4, active_explode.duration)
            s_dur = active_explode.scatter_duration if active_explode.scatter_duration is not None else 0.4
            h_dur = active_explode.hold_duration if active_explode.hold_duration is not None else 1.2
            r_dur = active_explode.reassemble_duration if active_explode.reassemble_duration is not None else 1.4

            total_dur = s_dur + h_dur + r_dur
            if abs(total_dur - dur) > 1e-4:
                factor = dur / total_dur
                s_dur *= factor
                h_dur *= factor
                r_dur *= factor

            S = float(active_explode.intensity if active_explode.intensity is not None else 1.0)
            easing_mode = active_explode.easing or "ease_in_out"

            if tau < s_dur:
                # Phase 1: Explosion outward
                u = tau / max(1e-4, s_dur)
                k = apply_easing(u, "ease_out")
                w_float = apply_easing(u, "ease_in") * 0.4
            elif tau < s_dur + h_dur:
                # Phase 2: Floating separated in air
                k = 1.0
                w_float = 1.0
            else:
                # Phase 3: Smooth reassembly
                v = (tau - (s_dur + h_dur)) / max(1e-4, r_dur)
                v = min(1.0, max(0.0, v))
                e_re = apply_easing(v, easing_mode)
                k = 1.0 - e_re
                w_float = (1.0 - v) * (1.0 - e_re)

            for layer in layers:
                name = layer.name.lower()
                dx = 0.0
                dy = 0.0
                drot = 0.0

                if any(h in name for h in ("head", "eyes", "mouth", "front_hair", "ear_accessory", "back_hair")):
                    base_dx = -16.0 * S
                    base_dy = -135.0 * S
                    base_rot = -12.0 * S
                    float_dx = 5.0 * math.sin(3.5 * tau)
                    float_dy = 7.0 * math.cos(2.8 * tau)
                    float_rot = 3.5 * math.sin(2.1 * tau)
                    dx = k * base_dx + w_float * float_dx
                    dy = k * base_dy + w_float * float_dy
                    drot = k * base_rot + w_float * float_rot

                elif "left" in name and ("arm" in name or "sleeve" in name or "prop" in name):
                    base_dx = -135.0 * S
                    base_dy = -50.0 * S
                    base_rot = 38.0 * S
                    float_dx = 6.0 * math.cos(3.0 * tau + 1.0)
                    float_dy = 8.0 * math.sin(2.5 * tau + 0.5)
                    float_rot = 5.0 * math.cos(2.0 * tau)
                    dx = k * base_dx + w_float * float_dx
                    dy = k * base_dy + w_float * float_dy
                    drot = k * base_rot + w_float * float_rot

                elif "right" in name and ("arm" in name or "sleeve" in name or "prop" in name):
                    base_dx = 140.0 * S
                    base_dy = -45.0 * S
                    base_rot = -40.0 * S
                    float_dx = -6.0 * math.sin(2.7 * tau + 0.8)
                    float_dy = 8.0 * math.cos(3.2 * tau + 1.2)
                    float_rot = -5.0 * math.sin(2.2 * tau)
                    dx = k * base_dx + w_float * float_dx
                    dy = k * base_dy + w_float * float_dy
                    drot = k * base_rot + w_float * float_rot

                elif "left_leg" in name:
                    base_dx = -85.0 * S
                    base_dy = 110.0 * S
                    base_rot = -22.0 * S
                    float_dx = 5.0 * math.sin(2.2 * tau + 2.0)
                    float_dy = 6.0 * math.cos(2.0 * tau + 1.5)
                    float_rot = 4.0 * math.sin(1.8 * tau)
                    dx = k * base_dx + w_float * float_dx
                    dy = k * base_dy + w_float * float_dy
                    drot = k * base_rot + w_float * float_rot

                elif "right_leg" in name:
                    base_dx = 85.0 * S
                    base_dy = 112.0 * S
                    base_rot = 22.0 * S
                    float_dx = -5.0 * math.cos(2.4 * tau + 0.3)
                    float_dy = 6.0 * math.sin(2.6 * tau + 0.7)
                    float_rot = -4.0 * math.cos(2.1 * tau)
                    dx = k * base_dx + w_float * float_dx
                    dy = k * base_dy + w_float * float_dy
                    drot = k * base_rot + w_float * float_rot

                elif any(b in name for b in ("body", "undershirt", "belt", "jacket_front_flaps", "jacket_back", "pants")):
                    base_dx = 0.0
                    base_dy = 20.0 * S
                    base_rot = 0.0
                    float_dx = 2.0 * math.sin(2.0 * tau)
                    float_dy = 3.5 * math.cos(2.5 * tau)
                    float_rot = 1.5 * math.sin(1.5 * tau)
                    dx = k * base_dx + w_float * float_dx
                    dy = k * base_dy + w_float * float_dy
                    drot = k * base_rot + w_float * float_rot

                layer.x += dx
                layer.y += dy
                layer.rotation += drot

        eval_explosion = None
        if active_explode is not None:
            eval_explosion = ExplosionState(
                active=True,
                tau=tau,
                duration=dur,
                scatter_duration=s_dur,
                hold_duration=h_dur,
                reassemble_duration=r_dur,
                intensity=S,
                fire=active_explode.fire_enabled,
                color=active_explode.fire_color,
            )

        # 5. Resolve Aura State
        aura_active = False
        aura_color = "gold"
        aura_sparks = True
        aura_intensity_events: List[Tuple[float, float, str, float, bool]] = []
        aura_size_events: List[Tuple[float, float, str, float, bool]] = []
        aura_speed_events: List[Tuple[float, float, str, float, bool]] = []

        for anim in self.animations:
            if anim.kind == "aura":
                if anim.start_time <= t + 1e-9:
                    if anim.aura_active is not None:
                        aura_active = anim.aura_active
                    if anim.aura_color:
                        aura_color = anim.aura_color
                    if anim.aura_sparks is not None:
                        aura_sparks = anim.aura_sparks

                if anim.aura_intensity is not None:
                    aura_intensity_events.append((anim.start_time, anim.duration, anim.easing, anim.aura_intensity, False))
                if anim.aura_size is not None:
                    aura_size_events.append((anim.start_time, anim.duration, anim.easing, anim.aura_size, False))
                if anim.aura_speed is not None:
                    aura_speed_events.append((anim.start_time, anim.duration, anim.easing, anim.aura_speed, False))

        aura_intensity = _evaluate_channel(t, 1.0, aura_intensity_events) if aura_intensity_events else 1.0
        aura_size = _evaluate_channel(t, 35.0, aura_size_events) if aura_size_events else 35.0
        aura_speed = _evaluate_channel(t, 1.0, aura_speed_events) if aura_speed_events else 1.0

        evaluated_aura = AuraState(
            active=aura_active,
            color=aura_color,
            intensity=aura_intensity,
            size=aura_size,
            speed=aura_speed,
            sparks=aura_sparks,
        )

        return AvatarState(
            identifier=self.identifier,
            character=self.character,
            x=x + offset_x,
            y=y + offset_y,
            scale=scale,
            rotation=rotation + offset_rot,
            opacity=opacity,
            expression=expr,
            is_blinking=is_blinking,
            layers=layers,
            aura=evaluated_aura,
            explosion=eval_explosion,
        )
