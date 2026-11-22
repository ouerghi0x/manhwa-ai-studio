"""Lark parse-tree to AvatarScript AST builder."""
from typing import Any, List, Tuple
from lark import Transformer, Token, Tree, v_args
from avatarscript.ast.nodes import (
    SourceLocation,
    SceneNode,
    ScenePropertyNode,
    AvatarNode,
    AvatarPropertyNode,
    IdleBlockNode,
    TimelineBlockNode,
    ExpressionNode,
    AnimationNode,
    HoldNode,
    TalkNode,
    HeadTurnNode,
    LookNode,
)


def _loc_from_meta(meta: Any) -> SourceLocation:
    line = getattr(meta, "line", 1)
    col = getattr(meta, "column", 1)
    return SourceLocation(line=line, column=col)


def _strip_quotes(s: str) -> str:
    if len(s) >= 2 and s[0] == '"' and s[-1] == '"':
        return s[1:-1]
    return s


def _parse_time(s: str) -> float:
    return float(str(s).rstrip("s"))


@v_args(meta=True)
class ASTBuilder(Transformer):
    def start(self, meta: Any, children: List[Any]) -> SceneNode:
        for ch in children:
            if isinstance(ch, SceneNode):
                return ch
        raise ValueError("No scene_def found in parse tree")

    def scene_def(self, meta: Any, children: List[Any]) -> SceneNode:
        name = _strip_quotes(str(children[0]))
        props: List[ScenePropertyNode] = []
        avatars: List[AvatarNode] = []
        for item in children[1:]:
            if isinstance(item, ScenePropertyNode):
                props.append(item)
            elif isinstance(item, AvatarNode):
                avatars.append(item)
        return SceneNode(loc=_loc_from_meta(meta), name=name, properties=props, avatars=avatars)

    def canvas_stmt(self, meta: Any, children: List[Any]) -> ScenePropertyNode:
        res_str = str(children[0])
        w_str, h_str = res_str.lower().split("x")
        return ScenePropertyNode(
            loc=_loc_from_meta(meta), name="canvas", value=(int(w_str), int(h_str))
        )

    def background_stmt(self, meta: Any, children: List[Any]) -> ScenePropertyNode:
        return ScenePropertyNode(
            loc=_loc_from_meta(meta), name="background", value=_strip_quotes(str(children[0]))
        )

    def fps_stmt(self, meta: Any, children: List[Any]) -> ScenePropertyNode:
        return ScenePropertyNode(
            loc=_loc_from_meta(meta), name="fps", value=float(str(children[0]))
        )

    def duration_stmt(self, meta: Any, children: List[Any]) -> ScenePropertyNode:
        return ScenePropertyNode(
            loc=_loc_from_meta(meta), name="duration", value=_parse_time(str(children[0]))
        )

    def render_stmt(self, meta: Any, children: List[Any]) -> ScenePropertyNode:
        return ScenePropertyNode(
            loc=_loc_from_meta(meta), name="render", value=_strip_quotes(str(children[0]))
        )

    def avatar_def(self, meta: Any, children: List[Any]) -> AvatarNode:
        ident = _strip_quotes(str(children[0]))
        props: List[AvatarPropertyNode] = []
        idle_node = None
        timeline_blocks: List[TimelineBlockNode] = []

        for item in children[1:]:
            if isinstance(item, (AvatarPropertyNode, HoldNode)):
                props.append(item)
            elif isinstance(item, IdleBlockNode):
                idle_node = item
            elif isinstance(item, TimelineBlockNode):
                timeline_blocks.append(item)

        return AvatarNode(
            loc=_loc_from_meta(meta),
            identifier=ident,
            properties=props,
            idle=idle_node,
            timeline_blocks=timeline_blocks,
        )

    def character_stmt(self, meta: Any, children: List[Any]) -> AvatarPropertyNode:
        return AvatarPropertyNode(
            loc=_loc_from_meta(meta), name="character", value=_strip_quotes(str(children[0]))
        )

    def position_stmt(self, meta: Any, children: List[Any]) -> AvatarPropertyNode:
        return AvatarPropertyNode(
            loc=_loc_from_meta(meta), name="position", value=children[0]
        )

    def named_pos(self, meta: Any, children: List[Any]) -> str:
        return str(children[0])

    def coord_pos(self, meta: Any, children: List[Any]) -> Tuple[float, float]:
        return children[0]

    def coord_pair(self, meta: Any, children: List[Any]) -> Tuple[float, float]:
        return (float(str(children[0])), float(str(children[1])))

    def scale_prop_stmt(self, meta: Any, children: List[Any]) -> AvatarPropertyNode:
        return AvatarPropertyNode(
            loc=_loc_from_meta(meta), name="scale", value=float(str(children[0]))
        )

    def rotation_prop_stmt(self, meta: Any, children: List[Any]) -> AvatarPropertyNode:
        return AvatarPropertyNode(
            loc=_loc_from_meta(meta), name="rotation", value=float(str(children[0]))
        )

    def hold_stmt(self, meta: Any, children: List[Any]) -> AvatarPropertyNode:
        item = "microphone"
        hand = "right"
        scale = 1.0
        for kind, val in children:
            if kind == "item":
                item = val
            elif kind == "hand":
                hand = val
            elif kind == "scale":
                scale = float(val)
            elif kind == "val":
                if val in ("left", "right"):
                    hand = val
                else:
                    item = val
        return AvatarPropertyNode(loc=_loc_from_meta(meta), name="hold", value=(item, hand, scale))

    def hold_item(self, meta: Any, children: List[Any]) -> Tuple[str, str]:
        return ("item", _strip_quotes(str(children[0])))

    def hold_hand(self, meta: Any, children: List[Any]) -> Tuple[str, str]:
        return ("hand", _strip_quotes(str(children[0])).lower())

    def hold_scale(self, meta: Any, children: List[Any]) -> Tuple[str, float]:
        return ("scale", float(str(children[0])))

    def hold_val(self, meta: Any, children: List[Any]) -> Tuple[str, str]:
        return ("val", _strip_quotes(str(children[0])).lower())

    def idle_block(self, meta: Any, children: List[Any]) -> IdleBlockNode:
        breathe = False
        blink_interval = None
        for kind, val in children:
            if kind == "breathe":
                breathe = True
            elif kind == "blink":
                blink_interval = val
        return IdleBlockNode(
            loc=_loc_from_meta(meta), breathe=breathe, blink_interval=blink_interval
        )

    def breathe_stmt(self, meta: Any, children: List[Any]) -> Tuple[str, bool]:
        return ("breathe", True)

    def blink_stmt(self, meta: Any, children: List[Any]) -> Tuple[str, float]:
        if children:
            return ("blink", _parse_time(str(children[0])))
        return ("blink", 4.0)

    def timeline_block(self, meta: Any, children: List[Any]) -> TimelineBlockNode:
        ts = _parse_time(str(children[0]))
        actions = [
            c for c in children[1:] if isinstance(c, (ExpressionNode, AnimationNode, AvatarPropertyNode, TalkNode, HeadTurnNode, LookNode))
        ]
        return TimelineBlockNode(loc=_loc_from_meta(meta), timestamp=ts, actions=actions)

    def head_turn_stmt(self, meta: Any, children: List[Any]) -> HeadTurnNode:
        yaw = 0.0
        pitch = 0.0
        duration = 0.3
        easing = "ease_in_out"
        for kind, val in children:
            if kind == "yaw":
                yaw = val
            elif kind == "pitch":
                pitch = val
            elif kind == "duration":
                duration = val
            elif kind == "easing":
                easing = val
        return HeadTurnNode(loc=_loc_from_meta(meta), yaw=yaw, pitch=pitch, duration=duration, easing=easing)

    def param_yaw(self, meta: Any, children: List[Any]) -> Tuple[str, float]:
        return ("yaw", float(str(children[0])))

    def param_pitch(self, meta: Any, children: List[Any]) -> Tuple[str, float]:
        return ("pitch", float(str(children[0])))

    def look_stmt(self, meta: Any, children: List[Any]) -> LookNode:
        target = None
        look_x = None
        look_y = None
        duration = 0.2
        easing = "ease_in_out"
        for kind, val in children:
            if kind == "look_at":
                target = val
            elif kind == "look_x":
                look_x = val
            elif kind == "look_y":
                look_y = val
            elif kind == "duration":
                duration = val
            elif kind == "easing":
                easing = val
        return LookNode(
            loc=_loc_from_meta(meta),
            target=target,
            look_x=look_x,
            look_y=look_y,
            duration=duration,
            easing=easing,
        )

    def param_look_at(self, meta: Any, children: List[Any]) -> Tuple[str, str]:
        return ("look_at", _strip_quotes(str(children[0])).lower())

    def param_look_x(self, meta: Any, children: List[Any]) -> Tuple[str, float]:
        return ("look_x", float(str(children[0])))

    def param_look_y(self, meta: Any, children: List[Any]) -> Tuple[str, float]:
        return ("look_y", float(str(children[0])))

    def talk_stmt(self, meta: Any, children: List[Any]) -> TalkNode:
        audio = None
        duration = None
        threshold = 0.12
        speed = 1.0
        for kind, val in children:
            if kind == "audio":
                audio = val
            elif kind == "duration":
                duration = val
            elif kind == "threshold":
                threshold = val
            elif kind == "speed":
                speed = val
        return TalkNode(loc=_loc_from_meta(meta), audio=audio, duration=duration, threshold=threshold, speed=speed)

    def talk_audio(self, meta: Any, children: List[Any]) -> Tuple[str, str]:
        return ("audio", _strip_quotes(str(children[0])))

    def talk_duration(self, meta: Any, children: List[Any]) -> Tuple[str, float]:
        return ("duration", _parse_time(str(children[0])))

    def talk_threshold(self, meta: Any, children: List[Any]) -> Tuple[str, float]:
        return ("threshold", float(str(children[0])))

    def talk_speed(self, meta: Any, children: List[Any]) -> Tuple[str, float]:
        return ("speed", float(str(children[0])))

    def expression_stmt(self, meta: Any, children: List[Any]) -> ExpressionNode:
        return ExpressionNode(loc=_loc_from_meta(meta), expression=str(children[0]))

    def animate_stmt(self, meta: Any, children: List[Any]) -> AnimationNode:
        kind = str(children[0])
        return self._build_anim_node(meta, kind, children[1:])

    def direct_transform_stmt(self, meta: Any, children: List[Any]) -> AnimationNode:
        kind = str(children[0])
        return self._build_anim_node(meta, kind, children[1:])

    def _build_anim_node(self, meta: Any, kind: str, raw_params: List[Any]) -> AnimationNode:
        duration = None
        easing = "ease_in_out"
        intensity = None
        params = {}
        scalar_target = None

        for p_type, p_val in raw_params:
            if p_type == "duration":
                duration = p_val
            elif p_type == "easing":
                easing = p_val
            elif p_type == "intensity":
                intensity = p_val
            elif p_type == "kv":
                k, v = p_val
                params[k] = v
            elif p_type == "val":
                scalar_target = p_val

        return AnimationNode(
            loc=_loc_from_meta(meta),
            kind=kind,
            duration=duration,
            easing=easing,
            intensity=intensity,
            params=params,
            scalar_target=scalar_target,
        )

    def param_duration(self, meta: Any, children: List[Any]) -> Tuple[str, float]:
        return ("duration", _parse_time(str(children[0])))

    def param_easing(self, meta: Any, children: List[Any]) -> Tuple[str, str]:
        return ("easing", str(children[0]))

    def param_intensity(self, meta: Any, children: List[Any]) -> Tuple[str, float]:
        return ("intensity", float(str(children[0])))

    def param_color(self, meta: Any, children: List[Any]) -> Tuple[str, Tuple[str, str]]:
        return ("kv", ("color", _strip_quotes(str(children[0]))))

    def param_size(self, meta: Any, children: List[Any]) -> Tuple[str, Tuple[str, float]]:
        return ("kv", ("size", float(str(children[0]))))

    def param_speed(self, meta: Any, children: List[Any]) -> Tuple[str, Tuple[str, float]]:
        return ("kv", ("speed", float(str(children[0]))))

    def param_sparks(self, meta: Any, children: List[Any]) -> Tuple[str, Tuple[str, Any]]:
        val_str = str(children[0]).lower()
        if val_str in ("1", "true", "on", "yes"):
            val: Any = True
        elif val_str in ("0", "false", "off", "no"):
            val = False
        else:
            val = bool(float(val_str))
        return ("kv", ("sparks", val))

    def param_separated(self, meta: Any, children: List[Any]) -> Tuple[str, Tuple[str, float]]:
        val_str = str(children[0])
        val = _parse_time(val_str) if val_str.endswith("s") else float(val_str)
        return ("kv", ("separated", val))

    def param_hold(self, meta: Any, children: List[Any]) -> Tuple[str, Tuple[str, float]]:
        val_str = str(children[0])
        val = _parse_time(val_str) if val_str.endswith("s") else float(val_str)
        return ("kv", ("hold", val))

    def param_reassemble(self, meta: Any, children: List[Any]) -> Tuple[str, Tuple[str, float]]:
        val_str = str(children[0])
        val = _parse_time(val_str) if val_str.endswith("s") else float(val_str)
        return ("kv", ("reassemble", val))

    def param_scatter(self, meta: Any, children: List[Any]) -> Tuple[str, Tuple[str, float]]:
        val_str = str(children[0])
        val = _parse_time(val_str) if val_str.endswith("s") else float(val_str)
        return ("kv", ("scatter", val))

    def param_fire(self, meta: Any, children: List[Any]) -> Tuple[str, Tuple[str, Any]]:
        val_str = _strip_quotes(str(children[0])).lower()
        if val_str in ("true", "1", "yes", "on"):
            return ("kv", ("fire", True))
        elif val_str in ("false", "0", "no", "off"):
            return ("kv", ("fire", False))
        return ("kv", ("fire", val_str))

    def param_name(self, meta: Any, children: List[Any]) -> Tuple[str, str]:
        return ("val", str(children[0]))

    def param_kv(self, meta: Any, children: List[Any]) -> Tuple[str, Tuple[str, Any]]:
        k = str(children[0])
        val_raw = str(children[1])
        if val_raw.endswith("s") and len(val_raw) > 1 and val_raw[:-1].replace(".", "", 1).isdigit():
            v: Any = _parse_time(val_raw)
        else:
            try:
                v = float(val_raw)
            except ValueError:
                v = _strip_quotes(val_raw)
        return ("kv", (k, v))

    def param_val(self, meta: Any, children: List[Any]) -> Tuple[str, float]:
        return ("val", float(str(children[0])))
