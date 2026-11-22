"""Semantic validator for AvatarScript AST."""
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Set
from avatarscript.ast.nodes import (
    SceneNode,
    AvatarNode,
    AvatarPropertyNode,
    ExpressionNode,
    AnimationNode,
    TalkNode,
    HeadTurnNode,
    LookNode,
    SourceLocation,
)
from avatarscript.runtime.expressions import VALID_EXPRESSIONS
from avatarscript.runtime.interpolation import EASING_FUNCTIONS

VALID_POSITIONS = {"left", "center", "right"}
VALID_ANIMATIONS = {
    "shake",
    "bounce",
    "move",
    "scale",
    "rotate",
    "fade",
    "nod",
    "arm",
    "left_arm",
    "right_arm",
    "leg",
    "left_leg",
    "right_leg",
    "walk",
    "run",
    "jump",
    "aura",
    "explode",
}


@dataclass
class ValidationError:
    message: str
    loc: SourceLocation

    def __str__(self) -> str:
        return f"Line {self.loc.line}, Col {self.loc.column}: {self.message}"


class AvatarValidationException(Exception):
    """Raised when semantic validation fails with one or more errors."""

    def __init__(self, errors: List[ValidationError]):
        self.errors = errors
        formatted = "\n".join(str(e) for e in errors)
        super().__init__(f"Semantic validation failed with {len(errors)} error(s):\n{formatted}")


class SemanticValidator:
    def __init__(self, assets_root: Optional[Path] = None):
        if assets_root is None:
            assets_root = Path(__file__).resolve().parent.parent.parent / "assets"
        self.assets_root = assets_root

    def validate(self, scene: SceneNode) -> List[ValidationError]:
        errors: List[ValidationError] = []

        # 1. Validate scene properties
        seen_scene_props: Set[str] = set()
        scene_duration: Optional[float] = None
        for prop in scene.properties:
            if prop.name in seen_scene_props:
                errors.append(
                    ValidationError(f"Duplicate scene property '{prop.name}'", prop.loc)
                )
            seen_scene_props.add(prop.name)

            if prop.name == "canvas":
                w, h = prop.value  # type: ignore
                if w <= 0 or h <= 0:
                    errors.append(
                        ValidationError(f"Invalid canvas resolution {w}x{h}", prop.loc)
                    )
            elif prop.name == "fps":
                fps = float(prop.value)  # type: ignore
                if fps <= 0 or fps > 240:
                    errors.append(
                        ValidationError(f"Invalid fps '{fps}' (must be between 1 and 240)", prop.loc)
                    )
            elif prop.name == "duration":
                dur = float(prop.value)  # type: ignore
                if dur <= 0:
                    errors.append(
                        ValidationError(f"Invalid scene duration '{dur}s' (must be > 0)", prop.loc)
                    )
                scene_duration = dur

        # 2. Validate avatars
        if not scene.avatars:
            errors.append(
                ValidationError(f"Scene '{scene.name}' must define at least one avatar", scene.loc)
            )

        seen_avatars: Set[str] = set()
        for avatar in scene.avatars:
            if avatar.identifier in seen_avatars:
                errors.append(
                    ValidationError(
                        f"Duplicate avatar identifier '{avatar.identifier}'", avatar.loc
                    )
                )
            seen_avatars.add(avatar.identifier)
            self._validate_avatar(avatar, scene_duration, errors)

        return errors

    def _prop_asset_exists(self, item_name: str) -> bool:
        """Check whether a prop exists as .svg or .png under assets/props."""
        props_dir = self.assets_root / "props"
        p = Path(item_name)
        if p.suffix.lower() in (".svg", ".png") and (props_dir / item_name).exists():
            return True
        stem = p.stem if p.suffix.lower() in (".svg", ".png") else item_name
        return (props_dir / f"{stem}.svg").exists() or (props_dir / f"{stem}.png").exists()

    def _validate_hold_prop(
        self,
        hold_val: tuple,
        loc: SourceLocation,
        errors: List[ValidationError],
    ) -> None:
        """Validate a hold item declaration or timeline action."""
        item_name = hold_val[0]
        hand_name = hold_val[1]
        item_scale = hold_val[2] if len(hold_val) > 2 else 1.0
        if hand_name not in ("left", "right"):
            errors.append(
                ValidationError(
                    f"Invalid hand '{hand_name}' for hold (allowed: 'left', 'right')",
                    loc,
                )
            )
        if item_scale <= 0:
            errors.append(
                ValidationError(
                    f"Prop scale must be positive (got {item_scale})",
                    loc,
                )
            )
        if item_name not in ("none", "off") and not self._prop_asset_exists(item_name):
            errors.append(
                ValidationError(
                    f"Prop '{item_name}' not found in {self.assets_root / 'props'} (.svg or .png, e.g. microphone, sword, controller, phone)",
                    loc,
                )
            )

    def _validate_avatar(
        self,
        avatar: AvatarNode,
        scene_duration: Optional[float],
        errors: List[ValidationError],
    ) -> None:
        seen_props: Set[str] = set()
        has_character = False

        for prop in avatar.properties:
            if prop.name in seen_props:
                errors.append(
                    ValidationError(
                        f"Duplicate property '{prop.name}' in avatar '{avatar.identifier}'",
                        prop.loc,
                    )
                )
            seen_props.add(prop.name)

            if prop.name == "character":
                has_character = True
                char_name = str(prop.value)
                char_dir = self.assets_root / "characters" / char_name
                if not char_dir.exists() or not char_dir.is_dir():
                    errors.append(
                        ValidationError(
                            f"Undefined character '{char_name}' (directory not found in {self.assets_root / 'characters'})",
                            prop.loc,
                        )
                    )
            elif prop.name == "position":
                if isinstance(prop.value, str) and prop.value not in VALID_POSITIONS:
                    errors.append(
                        ValidationError(
                            f"Invalid named position '{prop.value}' (allowed: {sorted(VALID_POSITIONS)})",
                            prop.loc,
                        )
                    )
            elif prop.name == "scale":
                if float(prop.value) <= 0:  # type: ignore
                    errors.append(
                        ValidationError(
                            f"Avatar scale must be positive (got {prop.value})", prop.loc
                        )
                    )
            elif prop.name == "hold":
                self._validate_hold_prop(prop.value, prop.loc, errors)  # type: ignore

        if not has_character:
            errors.append(
                ValidationError(
                    f"Avatar '{avatar.identifier}' is missing required 'character' declaration",
                    avatar.loc,
                )
            )

        if avatar.idle and avatar.idle.blink_interval is not None:
            if avatar.idle.blink_interval <= 0.15:
                errors.append(
                    ValidationError(
                        f"Blink interval must be > 0.15s (got {avatar.idle.blink_interval}s)",
                        avatar.idle.loc,
                    )
                )

        for tb in avatar.timeline_blocks:
            if tb.timestamp < 0:
                errors.append(
                    ValidationError(f"Timeline timestamp cannot be negative ({tb.timestamp}s)", tb.loc)
                )
            if scene_duration is not None and tb.timestamp > scene_duration:
                errors.append(
                    ValidationError(
                        f"Timeline timestamp {tb.timestamp}s exceeds scene duration {scene_duration}s",
                        tb.loc,
                    )
                )
            for act in tb.actions:
                if isinstance(act, ExpressionNode):
                    if act.expression not in VALID_EXPRESSIONS:
                        errors.append(
                            ValidationError(
                                f"Unknown expression '{act.expression}' (allowed: {sorted(VALID_EXPRESSIONS)})",
                                act.loc,
                            )
                        )
                elif isinstance(act, AvatarPropertyNode) and act.name == "hold":
                    self._validate_hold_prop(act.value, act.loc, errors)  # type: ignore
                elif isinstance(act, TalkNode):
                    if act.audio:
                        audio_path = Path(act.audio)
                        if not audio_path.is_absolute():
                            audio_path = self.assets_root.parent / audio_path
                        if not audio_path.exists():
                            # Check under workspace root as fallback
                            candidates = [
                                Path.cwd() / act.audio,
                                Path.cwd() / "content" / act.audio,
                                Path.cwd().parent / "content" / act.audio,
                                Path.cwd().parent / act.audio,
                            ]
                            found = any(c.exists() for c in candidates)
                            if not found:
                                errors.append(
                                    ValidationError(f"Audio file '{act.audio}' not found", act.loc)
                                )
                    elif act.duration is None or act.duration <= 0:
                        errors.append(
                            ValidationError("Talk action requires either an audio file or positive duration", act.loc)
                        )
                elif isinstance(act, HeadTurnNode):
                    if act.duration is None or act.duration <= 0:
                        errors.append(
                            ValidationError("Head turn requires a positive duration (e.g. 'duration 0.3s')", act.loc)
                        )
                    if act.easing not in EASING_FUNCTIONS:
                        errors.append(
                            ValidationError(f"Unknown easing '{act.easing}' for head_turn", act.loc)
                        )
                elif isinstance(act, LookNode):
                    if act.duration is None or act.duration <= 0:
                        errors.append(
                            ValidationError("Look action requires a positive duration (e.g. 'duration 0.2s')", act.loc)
                        )
                    if act.easing not in EASING_FUNCTIONS:
                        errors.append(
                            ValidationError(f"Unknown easing '{act.easing}' for look", act.loc)
                        )
                    valid_look_targets = {"left", "right", "up", "down", "center"}
                    if act.target is not None and act.target not in valid_look_targets:
                        errors.append(
                            ValidationError(
                                f"Invalid look target '{act.target}' (allowed: {sorted(valid_look_targets)})",
                                act.loc,
                            )
                        )
                elif isinstance(act, AnimationNode):
                    self._validate_animation(act, errors)

    def _validate_animation(
        self, anim: AnimationNode, errors: List[ValidationError]
    ) -> None:
        if anim.kind not in VALID_ANIMATIONS:
            errors.append(
                ValidationError(
                    f"Unknown animation kind '{anim.kind}' (allowed: {sorted(VALID_ANIMATIONS)})",
                    anim.loc,
                )
            )
            return

        if (anim.duration is None or anim.duration <= 0) and anim.kind != "aura":
            errors.append(
                ValidationError(
                    f"Animation '{anim.kind}' requires a positive duration (e.g. 'duration 0.4s')",
                    anim.loc,
                )
            )

        if anim.easing not in EASING_FUNCTIONS:
            errors.append(
                ValidationError(
                    f"Unknown easing function '{anim.easing}' (allowed: {sorted(EASING_FUNCTIONS.keys())})",
                    anim.loc,
                )
            )

        if anim.kind == "move":
            unknown_keys = set(anim.params.keys()) - {"x", "y", "to_x", "to_y"}
            if unknown_keys:
                errors.append(
                    ValidationError(
                        f"Invalid parameter(s) {sorted(unknown_keys)} for 'move' animation",
                        anim.loc,
                    )
                )
            if not anim.params:
                errors.append(
                    ValidationError(
                        "Animation 'move' requires target coordinates (e.g. 'x:30 y:0')",
                        anim.loc,
                    )
                )
        elif anim.kind in ("walk", "run", "jump"):
            unknown_keys = set(anim.params.keys()) - {"x", "y", "to_x", "to_y", "height", "speed"}
            if unknown_keys:
                errors.append(
                    ValidationError(
                        f"Invalid parameter(s) {sorted(unknown_keys)} for '{anim.kind}' animation",
                        anim.loc,
                    )
                )
            if "speed" in anim.params and float(anim.params["speed"]) <= 0:
                errors.append(
                    ValidationError(
                        f"Animation '{anim.kind}' speed must be positive (got {anim.params['speed']})",
                        anim.loc,
                    )
                )
        elif anim.kind == "scale":
            target = anim.scalar_target if anim.scalar_target is not None else anim.params.get("to")
            if target is not None and target <= 0:
                errors.append(
                    ValidationError(f"Target scale must be positive (got {target})", anim.loc)
                )
        elif anim.kind == "fade":
            target = anim.scalar_target if anim.scalar_target is not None else anim.params.get("to")
            if target is not None and not (0.0 <= target <= 1.0):
                errors.append(
                    ValidationError(
                        f"Target opacity for 'fade' must be between 0.0 and 1.0 (got {target})",
                        anim.loc,
                    )
                )
        elif anim.kind == "explode":
            allowed_keys = {
                "separated",
                "hold",
                "float",
                "reassemble",
                "reassembly",
                "return",
                "scatter",
                "explode",
                "burst",
                "intensity",
                "speed",
                "shake",
                "fire",
                "flame",
                "color",
                "sparks",
                "smoke",
            }
            unknown_keys = set(anim.params.keys()) - allowed_keys
            if unknown_keys:
                errors.append(
                    ValidationError(
                        f"Invalid parameter(s) {sorted(unknown_keys)} for 'explode' animation",
                        anim.loc,
                    )
                )
