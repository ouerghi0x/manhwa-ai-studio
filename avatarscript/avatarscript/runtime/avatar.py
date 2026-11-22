"""Layer-based 2D Avatar model and deterministic state representation."""
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional
from avatarscript.runtime.expressions import resolve_expression_assets
from avatarscript.renderer.aura_renderer import AuraState
from avatarscript.renderer.explosion_renderer import ExplosionState


@dataclass
class LayerState:
    name: str
    asset_filename: str
    z_order: float = 0.0
    x: float = 0.0
    y: float = 0.0
    scale_x: float = 1.0
    scale_y: float = 1.0
    rotation: float = 0.0
    rotation_center: Tuple[float, float] = (200.0, 250.0)
    visible: bool = True
    opacity: float = 1.0
    is_prop: bool = False


@dataclass
class AvatarState:
    """Complete deterministic state of an avatar at a given timestamp t."""
    identifier: str
    character: str
    x: float
    y: float
    scale: float = 1.0
    rotation: float = 0.0
    opacity: float = 1.0
    expression: str = "neutral"
    is_blinking: bool = False
    layers: List[LayerState] = field(default_factory=list)
    aura: AuraState = field(default_factory=AuraState)
    explosion: Optional[ExplosionState] = None


@dataclass(frozen=True)
class CharacterRigConfig:
    """Rig proportions, anchor points, and joint sockets for 2D modular characters."""
    head_anchor: Tuple[float, float] = (200.0, 140.0)
    neck_anchor: Tuple[float, float] = (200.0, 204.0)
    shoulder_left: Tuple[float, float] = (130.0, 215.0)
    shoulder_right: Tuple[float, float] = (270.0, 215.0)
    hip_anchor: Tuple[float, float] = (200.0, 310.0)
    hip_left: Tuple[float, float] = (165.0, 315.0)
    hip_right: Tuple[float, float] = (235.0, 315.0)
    ear_left: Tuple[float, float] = (152.0, 144.0)
    ear_right: Tuple[float, float] = (248.0, 144.0)
    hand_socket_left: Tuple[float, float] = (110.0, 305.0)
    hand_socket_right: Tuple[float, float] = (290.0, 305.0)
    outline_stroke_width: float = 2.5
    is_pixel_art: bool = False


CHARACTER_RIG_CONFIGS: Dict[str, CharacterRigConfig] = {
    "default": CharacterRigConfig(
        head_anchor=(200.0, 140.0),
        neck_anchor=(200.0, 200.0),
        shoulder_left=(95.0, 265.0),
        shoulder_right=(305.0, 265.0),
        hip_anchor=(200.0, 372.0),
        hip_left=(162.0, 372.0),
        hip_right=(238.0, 372.0),
        ear_left=(145.0, 140.0),
        ear_right=(255.0, 140.0),
        hand_socket_left=(82.0, 330.0),
        hand_socket_right=(318.0, 330.0),
        outline_stroke_width=2.5,
    ),
    "jin": CharacterRigConfig(
        head_anchor=(200.0, 140.0),
        neck_anchor=(200.0, 204.0),
        shoulder_left=(130.0, 215.0),
        shoulder_right=(270.0, 215.0),
        hip_anchor=(200.0, 310.0),
        hip_left=(165.0, 315.0),
        hip_right=(235.0, 315.0),
        ear_left=(152.0, 144.0),
        ear_right=(248.0, 144.0),
        hand_socket_left=(110.0, 305.0),
        hand_socket_right=(290.0, 305.0),
        outline_stroke_width=2.5,
    ),
    "medazizwerghi": CharacterRigConfig(
        head_anchor=(200.0, 140.0),
        neck_anchor=(200.0, 204.0),
        shoulder_left=(130.0, 215.0),
        shoulder_right=(270.0, 215.0),
        hip_anchor=(200.0, 310.0),
        hip_left=(165.0, 315.0),
        hip_right=(235.0, 315.0),
        ear_left=(152.0, 144.0),
        ear_right=(248.0, 144.0),
        hand_socket_left=(110.0, 305.0),
        hand_socket_right=(290.0, 305.0),
        outline_stroke_width=2.5,
    ),
    "flame_emperor": CharacterRigConfig(
        head_anchor=(200.0, 140.0),
        neck_anchor=(200.0, 204.0),
        shoulder_left=(130.0, 215.0),
        shoulder_right=(270.0, 215.0),
        hip_anchor=(200.0, 310.0),
        hip_left=(165.0, 315.0),
        hip_right=(235.0, 315.0),
        ear_left=(152.0, 144.0),
        ear_right=(248.0, 144.0),
        hand_socket_left=(110.0, 305.0),
        hand_socket_right=(290.0, 305.0),
        outline_stroke_width=2.5,
        is_pixel_art=True,
    ),
    "pixel_narrator": CharacterRigConfig(
        head_anchor=(200.0, 140.0),
        neck_anchor=(200.0, 204.0),
        shoulder_left=(130.0, 215.0),
        shoulder_right=(270.0, 215.0),
        hip_anchor=(200.0, 310.0),
        hip_left=(165.0, 315.0),
        hip_right=(235.0, 315.0),
        ear_left=(152.0, 144.0),
        ear_right=(248.0, 144.0),
        hand_socket_left=(110.0, 305.0),
        hand_socket_right=(290.0, 305.0),
        outline_stroke_width=2.5,
        is_pixel_art=True,
    ),
    "streamer": CharacterRigConfig(
        head_anchor=(200.0, 140.0),
        neck_anchor=(200.0, 204.0),
        shoulder_left=(130.0, 215.0),
        shoulder_right=(270.0, 215.0),
        hip_anchor=(200.0, 310.0),
        hip_left=(165.0, 315.0),
        hip_right=(235.0, 315.0),
        ear_left=(152.0, 144.0),
        ear_right=(248.0, 144.0),
        hand_socket_left=(110.0, 305.0),
        hand_socket_right=(290.0, 305.0),
        outline_stroke_width=2.5,
        is_pixel_art=True,
    ),
}


def get_character_rig_config(char_name: str) -> CharacterRigConfig:
    return CHARACTER_RIG_CONFIGS.get(char_name.lower(), CharacterRigConfig())


def resolve_named_position(pos_name: str, canvas_width: int, canvas_height: int) -> Tuple[float, float]:
    """Resolve preset positions ('left', 'center', 'right') to pixel coordinates."""
    cy = canvas_height * 0.60
    if pos_name == "left":
        return (canvas_width * 0.25, cy)
    if pos_name == "right":
        return (canvas_width * 0.75, cy)
    return (canvas_width * 0.50, cy)


def build_default_layers(
    character: str = "default",
    expression: str = "neutral",
    is_blinking: bool = False,
    breathe_offset_y: float = 0.0,
    breathe_scale_y: float = 1.0,
    left_arm_rot: float = 0.0,
    right_arm_rot: float = 0.0,
    left_leg_rot: float = 0.0,
    right_leg_rot: float = 0.0,
    left_prop: str = "none",
    right_prop: str = "none",
    left_prop_scale: float = 1.0,
    right_prop_scale: float = 1.0,
    yaw: float = 0.0,
    pitch: float = 0.0,
    look_x: float = 0.0,
    look_y: float = 0.0,
) -> List[LayerState]:
    """Construct the ordered layer rig for a character at a specific state with 2.5D depth parallax."""
    expr_assets = resolve_expression_assets(expression, is_blinking=is_blinking)
    cfg = get_character_rig_config(character)

    # 2.5D Parallax & Perspective depth factors:
    ny = yaw / 45.0
    np = pitch / 30.0

    head_dx = ny * 6.0
    head_dy = np * 4.0

    eyes_dx = ny * 24.0 + look_x
    eyes_dy = np * 14.0 + look_y
    eyes_scale_x = max(0.2, 1.0 - 0.20 * abs(ny))

    mouth_dx = ny * 18.0
    mouth_dy = np * 12.0
    mouth_scale_x = max(0.2, 1.0 - 0.16 * abs(ny))

    body_dx = -ny * 2.0
    body_dy = np * 1.5

    layers = [
        # 0: Back hair / long hair extensions / cape
        LayerState(
            name="back_hair",
            asset_filename="back_hair.png",
            z_order=0.0,
            x=head_dx,
            y=breathe_offset_y + head_dy,
        ),
        # 1: Jacket/Coat BACK interior (inside lining visible behind torso)
        LayerState(
            name="jacket_back",
            asset_filename="jacket_back.png",
            z_order=1.0,
            x=body_dx,
            y=breathe_offset_y * 0.4 + body_dy,
            scale_y=breathe_scale_y,
        ),
        # 2: Base body (neck, torso, legs base)
        LayerState(
            name="body",
            asset_filename="body.svg",
            z_order=2.0,
            x=body_dx,
            y=breathe_offset_y * 0.4 + body_dy,
            scale_y=breathe_scale_y,
        ),
        # 3: Pants / bottoms & footwear (or animated legs left_leg & right_leg)
        LayerState(
            name="left_leg",
            asset_filename="left_leg.svg",
            z_order=3.0,
            x=body_dx,
            y=breathe_offset_y * 0.2 + body_dy,
            rotation=left_leg_rot,
            rotation_center=cfg.hip_left,
        ),
        LayerState(
            name="right_leg",
            asset_filename="right_leg.svg",
            z_order=3.1,
            x=body_dx,
            y=breathe_offset_y * 0.2 + body_dy,
            rotation=right_leg_rot,
            rotation_center=cfg.hip_right,
        ),
        LayerState(
            name="pants",
            asset_filename="pants.png",
            z_order=3.2,
            x=body_dx,
            y=breathe_offset_y * 0.2 + body_dy,
        ),
        # 4: Belt / waist accessories (anchored cleanly to the hip joint)
        LayerState(
            name="belt",
            asset_filename="belt.png",
            z_order=4.0,
            x=body_dx,
            y=breathe_offset_y * 0.3 + body_dy,
        ),
        # 5: Undershirt / inner top (tucked or layered cleanly above pants/belt)
        LayerState(
            name="undershirt",
            asset_filename="undershirt.png",
            z_order=5.0,
            x=body_dx,
            y=breathe_offset_y * 0.4 + body_dy,
            scale_y=breathe_scale_y,
        ),
        # 6: Head base, ears, and facial features
        LayerState(
            name="head",
            asset_filename="head.svg",
            z_order=6.0,
            x=head_dx,
            y=breathe_offset_y + head_dy,
        ),
        LayerState(
            name="eyes",
            asset_filename=expr_assets.eyes_asset,
            z_order=6.1,
            x=eyes_dx,
            y=breathe_offset_y + eyes_dy,
            scale_x=eyes_scale_x,
        ),
        LayerState(
            name="mouth",
            asset_filename=expr_assets.mouth_asset,
            z_order=6.2,
            x=mouth_dx,
            y=breathe_offset_y + mouth_dy,
            scale_x=mouth_scale_x,
        ),
        # 7: Ear accessories (earrings / AirPods anchored directly to ear coordinate center)
        LayerState(
            name="ear_accessory",
            asset_filename="ear_accessory.png",
            z_order=7.0,
            x=head_dx,
            y=breathe_offset_y + head_dy,
        ),
        # 8: Front hair & bangs (unified silhouette)
        LayerState(
            name="front_hair",
            asset_filename="front_hair.png",
            z_order=8.0,
            x=head_dx,
            y=breathe_offset_y + head_dy,
        ),
        # 9: Arms & hands (positioned at the shoulder sockets)
        LayerState(
            name="left_arm",
            asset_filename="left_arm.svg",
            z_order=9.0,
            x=-ny * 4.0,
            y=breathe_offset_y * 0.6,
            rotation=left_arm_rot,
            rotation_center=cfg.shoulder_left,
        ),
        LayerState(
            name="right_arm",
            asset_filename="right_arm.svg",
            z_order=9.1,
            x=-ny * 4.0,
            y=breathe_offset_y * 0.6,
            rotation=right_arm_rot,
            rotation_center=cfg.shoulder_right,
        ),
        # 10: Jacket/Coat SLEEVES (render OVER arms and match arm angle/pose)
        LayerState(
            name="jacket_sleeve_left",
            asset_filename="jacket_sleeve_left.png",
            z_order=10.0,
            x=-ny * 4.0,
            y=breathe_offset_y * 0.6,
            rotation=left_arm_rot,
            rotation_center=cfg.shoulder_left,
        ),
        LayerState(
            name="jacket_sleeve_right",
            asset_filename="jacket_sleeve_right.png",
            z_order=10.1,
            x=-ny * 4.0,
            y=breathe_offset_y * 0.6,
            rotation=right_arm_rot,
            rotation_center=cfg.shoulder_right,
        ),
        # 11: Jacket/Coat FRONT panels (framing inner shirt WITHOUT covering arms/hands)
        LayerState(
            name="jacket_front_flaps",
            asset_filename="jacket_front_flaps.png",
            z_order=11.0,
            x=body_dx,
            y=breathe_offset_y * 0.4 + body_dy,
            scale_y=breathe_scale_y,
        ),
    ]

    def _prop_asset_filename(name: str) -> str:
        lower = name.lower()
        return name if lower.endswith((".svg", ".png")) else f"{name}.svg"

    # Attach left hand prop if equipped (Z=12.0, in front of sleeves/hands)
    if left_prop and left_prop.lower() not in ("none", "off"):
        layers.append(
            LayerState(
                name="prop_left",
                asset_filename=_prop_asset_filename(left_prop),
                z_order=12.0,
                x=-ny * 4.0,
                y=breathe_offset_y * 0.6,
                scale_x=left_prop_scale,
                scale_y=left_prop_scale,
                rotation=left_arm_rot,
                rotation_center=cfg.shoulder_left,
                is_prop=True,
            )
        )

    # Attach right hand prop if equipped (Z=12.1, in front of sleeves/hands)
    if right_prop and right_prop.lower() not in ("none", "off"):
        layers.append(
            LayerState(
                name="prop_right",
                asset_filename=_prop_asset_filename(right_prop),
                z_order=12.1,
                x=-ny * 4.0,
                y=breathe_offset_y * 0.6,
                scale_x=right_prop_scale,
                scale_y=right_prop_scale,
                rotation=right_arm_rot,
                rotation_center=cfg.shoulder_right,
                is_prop=True,
            )
        )

    return sorted(layers, key=lambda l: l.z_order)
