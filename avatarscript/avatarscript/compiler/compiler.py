"""Compiler lowering AvatarScript AST into the runtime Intermediate Representation (IR)."""
from pathlib import Path
from typing import Dict, Optional, Tuple
from avatarscript.parser import AvatarParser
from avatarscript.ast.nodes import (
    SceneNode,
    AvatarNode,
    AvatarPropertyNode,
    ExpressionNode,
    AnimationNode,
    TalkNode,
    HeadTurnNode,
    LookNode,
)
from avatarscript.compiler.validator import SemanticValidator, AvatarValidationException
from avatarscript.runtime.scene import Scene
from avatarscript.runtime.avatar import resolve_named_position
from avatarscript.runtime.animation import (
    AvatarTimeline,
    AnimationEvent,
    ExpressionEvent,
    HoldEvent,
    TalkEvent,
    HeadTurnEvent,
    LookEvent,
    IdleConfig,
)


class AvatarCompiler:
    def __init__(self, assets_root: Optional[Path] = None):
        self.parser = AvatarParser()
        self.validator = SemanticValidator(assets_root=assets_root)

    def compile_source(self, source_text: str) -> Scene:
        """Parse, validate, and compile an .ava source string into a Scene IR."""
        ast_scene = self.parser.parse(source_text)
        errors = self.validator.validate(ast_scene)
        if errors:
            raise AvatarValidationException(errors)
        return self.lower_to_ir(ast_scene)

    def compile_file(self, path: Path) -> Scene:
        source_text = Path(path).read_text(encoding="utf-8")
        return self.compile_source(source_text)

    def lower_to_ir(self, ast_scene: SceneNode) -> Scene:
        width, height = 1920, 1080
        background = "#202020"
        fps = 30
        duration = 10.0
        output_path: Optional[str] = None

        for prop in ast_scene.properties:
            if prop.name == "canvas":
                width, height = prop.value  # type: ignore
            elif prop.name == "background":
                background = str(prop.value)
            elif prop.name == "fps":
                fps = int(round(float(prop.value)))  # type: ignore
            elif prop.name == "duration":
                duration = float(prop.value)  # type: ignore
            elif prop.name == "render":
                output_path = str(prop.value)

        avatars: Dict[str, AvatarTimeline] = {}
        for av_node in ast_scene.avatars:
            avatars[av_node.identifier] = self._lower_avatar(av_node, width, height)

        return Scene(
            name=ast_scene.name,
            width=width,
            height=height,
            background=background,
            fps=fps,
            duration=duration,
            output_path=output_path,
            avatars=avatars,
        )

    def _lower_avatar(self, av_node: AvatarNode, canvas_w: int, canvas_h: int) -> AvatarTimeline:
        character = "default"
        init_x, init_y = resolve_named_position("center", canvas_w, canvas_h)
        init_scale = 1.0
        init_rot = 0.0
        init_left_prop = "none"
        init_right_prop = "none"
        init_left_prop_scale = 1.0
        init_right_prop_scale = 1.0

        for prop in av_node.properties:
            if prop.name == "character":
                character = str(prop.value)
            elif prop.name == "position":
                if isinstance(prop.value, str):
                    init_x, init_y = resolve_named_position(prop.value, canvas_w, canvas_h)
                else:
                    init_x, init_y = float(prop.value[0]), float(prop.value[1])
            elif prop.name == "scale":
                init_scale = float(prop.value)  # type: ignore
            elif prop.name == "rotation":
                init_rot = float(prop.value)  # type: ignore
            elif prop.name == "hold":
                hold_val = prop.value
                item_name = hold_val[0]
                hand_name = hold_val[1]
                item_scale = float(hold_val[2]) if len(hold_val) > 2 else 1.0
                if hand_name == "left":
                    init_left_prop = item_name
                    init_left_prop_scale = item_scale
                else:
                    init_right_prop = item_name
                    init_right_prop_scale = item_scale

        idle_cfg = IdleConfig()
        if av_node.idle:
            idle_cfg = IdleConfig(
                breathe=av_node.idle.breathe,
                blink_interval=av_node.idle.blink_interval,
            )

        expr_events = []
        anim_events = []
        hold_events = []
        talk_events = []
        head_turn_events = []
        look_events = []

        for tb in sorted(av_node.timeline_blocks, key=lambda b: b.timestamp):
            for act in tb.actions:
                if isinstance(act, ExpressionNode):
                    expr_events.append(
                        ExpressionEvent(timestamp=tb.timestamp, expression=act.expression)
                    )
                elif isinstance(act, AvatarPropertyNode) and act.name == "hold":
                    hold_val = act.value
                    item_name = hold_val[0]
                    hand_name = hold_val[1]
                    item_scale = float(hold_val[2]) if len(hold_val) > 2 else 1.0
                    hold_events.append(
                        HoldEvent(timestamp=tb.timestamp, item=item_name, hand=hand_name, scale=item_scale)
                    )
                elif isinstance(act, TalkNode):
                    # If audio specified and duration omitted, get audio duration via ffprobe/lipsync
                    dur = act.duration if act.duration is not None else 1.0
                    if act.audio and act.duration is None:
                        audio_p = Path(act.audio)
                        if not audio_p.is_absolute() and not audio_p.exists():
                            cand = Path.cwd() / act.audio
                            if cand.exists():
                                audio_p = cand
                        from avatarscript.runtime.lipsync import AudioSpeechAnalyzer
                        env = AudioSpeechAnalyzer.load_audio_envelope(audio_p)
                        if len(env.time_points) > 0:
                            dur = float(env.time_points[-1])
                    talk_events.append(
                        TalkEvent(
                            timestamp=tb.timestamp,
                            audio=act.audio,
                            duration=dur,
                            threshold=act.threshold,
                            speed=act.speed,
                        )
                    )
                elif isinstance(act, HeadTurnNode):
                    dur = act.duration if act.duration is not None else 0.3
                    head_turn_events.append(
                        HeadTurnEvent(
                            start_time=tb.timestamp,
                            duration=dur,
                            yaw=act.yaw,
                            pitch=act.pitch,
                            easing=act.easing,
                        )
                    )
                elif isinstance(act, LookNode):
                    dur = act.duration if act.duration is not None else 0.2
                    look_events.append(
                        LookEvent(
                            start_time=tb.timestamp,
                            duration=dur,
                            target=act.target,
                            look_x=act.look_x,
                            look_y=act.look_y,
                            easing=act.easing,
                        )
                    )
                elif isinstance(act, AnimationNode):
                    ev = self._lower_animation(act, tb.timestamp)
                    anim_events.append(ev)

        return AvatarTimeline(
            identifier=av_node.identifier,
            character=character,
            initial_x=init_x,
            initial_y=init_y,
            initial_scale=init_scale,
            initial_rotation=init_rot,
            initial_left_prop=init_left_prop,
            initial_right_prop=init_right_prop,
            initial_left_prop_scale=init_left_prop_scale,
            initial_right_prop_scale=init_right_prop_scale,
            idle=idle_cfg,
            expressions=expr_events,
            hold_events=hold_events,
            talk_events=talk_events,
            head_turn_events=head_turn_events,
            look_events=look_events,
            animations=anim_events,
        )

    @staticmethod
    def _extract_limb_control(act: AnimationNode, kind_prefix: str) -> Tuple[str, Optional[float]]:
        """Extract limb target ('left', 'right') and angle for arm/leg animations."""
        angle = act.scalar_target
        if angle is None:
            for key in ("deg", "angle"):
                if key in act.params:
                    angle = float(act.params[key])
                    break
        if angle is None:
            angle = act.intensity

        if act.kind == f"left_{kind_prefix}":
            return "left", angle
        if act.kind == f"right_{kind_prefix}":
            return "right", angle
        if "left" in act.params:
            return "left", float(act.params["left"])
        if "right" in act.params:
            return "right", float(act.params["right"])
        return "right", angle

    def _lower_animation(self, act: AnimationNode, start_time: float) -> AnimationEvent:
        dur = act.duration if act.duration is not None else 0.5
        intensity = act.intensity if act.intensity is not None else 15.0
        anim_speed = float(act.params.get("speed", 1.0))

        target_x = None
        target_y = None
        delta_x = None
        delta_y = None
        target_scale = None
        target_rot = None
        target_opacity = None
        target_arm = None
        arm_angle = None
        target_leg = None
        leg_angle = None

        if act.kind in ("move", "walk", "run", "jump"):
            if "to_x" in act.params or "to_y" in act.params:
                target_x = act.params.get("to_x")
                target_y = act.params.get("to_y")
            elif act.kind == "move":
                delta_x = act.params.get("x", 0.0)
                delta_y = act.params.get("y", 0.0)
            else:
                delta_x = act.params.get("x")
                delta_y = act.params.get("y")

        if act.kind == "jump":
            if "height" in act.params:
                intensity = float(act.params["height"])
            elif act.intensity is not None:
                intensity = float(act.intensity)
            elif act.scalar_target is not None:
                intensity = float(act.scalar_target)
            else:
                intensity = 90.0
        elif act.kind == "scale":
            target_scale = (
                act.scalar_target if act.scalar_target is not None else act.params.get("to", 1.0)
            )
        elif act.kind == "rotate":
            target_rot = (
                act.scalar_target if act.scalar_target is not None else act.params.get("deg", 0.0)
            )
        elif act.kind == "fade":
            target_opacity = (
                act.scalar_target if act.scalar_target is not None else act.params.get("to", 1.0)
            )
        elif act.kind in ("arm", "left_arm", "right_arm"):
            target_arm, arm_angle = self._extract_limb_control(act, "arm")
            target_rot = arm_angle
        elif act.kind in ("leg", "left_leg", "right_leg"):
            target_leg, leg_angle = self._extract_limb_control(act, "leg")
            target_rot = leg_angle

        aura_active = None
        aura_color = None
        aura_intensity = None
        aura_size = None
        aura_speed = None
        aura_sparks = None

        if act.kind == "aura":
            # If scalar_target is 'none' or 'off' -> deactivate aura
            raw_target = str(act.scalar_target).lower() if act.scalar_target is not None else ""
            if raw_target in ("none", "off", "0", "false"):
                aura_active = False
            else:
                aura_active = True
                if raw_target:
                    aura_color = raw_target

            if "color" in act.params:
                aura_color = str(act.params["color"])
            if "intensity" in act.params:
                aura_intensity = float(act.params["intensity"])
            elif act.intensity is not None:
                aura_intensity = float(act.intensity)
            if "size" in act.params:
                aura_size = float(act.params["size"])
            if "speed" in act.params:
                aura_speed = float(act.params["speed"])
            if "sparks" in act.params:
                sparks_val = act.params["sparks"]
                if isinstance(sparks_val, bool):
                    aura_sparks = sparks_val
                elif isinstance(sparks_val, (int, float)):
                    aura_sparks = sparks_val > 0
                else:
                    aura_sparks = str(sparks_val).lower() not in ("0", "false", "off", "no")

        hold_duration = None
        for k in ("separated", "hold", "float"):
            if k in act.params:
                val = act.params[k]
                hold_duration = float(str(val).rstrip("s"))
                break

        reassemble_duration = None
        for k in ("reassemble", "reassembly", "return"):
            if k in act.params:
                val = act.params[k]
                reassemble_duration = float(str(val).rstrip("s"))
                break

        scatter_duration = None
        for k in ("scatter", "explode", "burst"):
            if k in act.params:
                val = act.params[k]
                scatter_duration = float(str(val).rstrip("s"))
                break

        if act.kind == "explode":
            if act.duration is None:
                if hold_duration is not None and reassemble_duration is not None:
                    s_dur = scatter_duration if scatter_duration is not None else 0.5
                    dur = s_dur + hold_duration + reassemble_duration
                else:
                    dur = 3.0

            if scatter_duration is None:
                if hold_duration is not None and reassemble_duration is not None and (hold_duration + reassemble_duration < dur):
                    scatter_duration = max(0.1, dur - hold_duration - reassemble_duration)
                else:
                    scatter_duration = max(0.2, min(0.6, dur * 0.20))

            if reassemble_duration is None:
                reassemble_duration = max(0.2, dur * 0.40)

            if hold_duration is None:
                hold_duration = max(0.0, dur - scatter_duration - reassemble_duration)

            intensity = float(act.params.get("intensity", act.intensity if act.intensity is not None else 1.0))

        fire_enabled = True
        fire_color = "orange"
        if act.kind == "explode":
            if "fire" in act.params:
                f_val = act.params["fire"]
                if isinstance(f_val, bool):
                    fire_enabled = f_val
                elif str(f_val).lower() in ("false", "0", "off", "none", "no"):
                    fire_enabled = False
                elif str(f_val).lower() in ("true", "1", "on", "yes"):
                    fire_enabled = True
                else:
                    fire_enabled = True
                    fire_color = str(f_val).lower()
            if "flame" in act.params:
                fl_val = act.params["flame"]
                if isinstance(fl_val, bool):
                    fire_enabled = fl_val
                else:
                    fire_enabled = True
                    fire_color = str(fl_val).lower()
            if "color" in act.params:
                fire_color = str(act.params["color"]).lower()

        return AnimationEvent(
            kind=act.kind,
            start_time=start_time,
            duration=dur,
            easing=act.easing,
            target_x=target_x,
            target_y=target_y,
            delta_x=delta_x,
            delta_y=delta_y,
            target_scale=target_scale,
            target_rotation=target_rot,
            target_opacity=target_opacity,
            intensity=intensity,
            target_arm=target_arm,
            arm_angle=arm_angle,
            target_leg=target_leg,
            leg_angle=leg_angle,
            anim_speed=anim_speed,
            aura_active=aura_active,
            aura_color=aura_color,
            aura_intensity=aura_intensity,
            aura_size=aura_size,
            aura_speed=aura_speed,
            aura_sparks=aura_sparks,
            hold_duration=hold_duration,
            reassemble_duration=reassemble_duration,
            scatter_duration=scatter_duration,
            fire_enabled=fire_enabled,
            fire_color=fire_color,
        )
