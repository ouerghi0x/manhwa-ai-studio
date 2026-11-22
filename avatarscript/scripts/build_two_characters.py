"""Modular 2D Character Generator for AvatarScript.

Implements strict Z-Index layer ordering, unified coordinate anchors,
zero-gap joint overlap (4-6px+ rule), solid pelvis/crotch bridge,
and procedural Canvas/Vector generation for:
1. `jin` (anime manhwa protagonist)
2. `medazizwerghi` (creator portrait with curly fade, beard, techwear jacket, AirPod)

Strict Z-Index Layer Order (Back to Front):
- 0: back_hair (or cape)
- 1: jacket_back (interior coat lining visible behind torso)
- 2: body (base body: neck, torso base, solid pelvis bridge)
- 3: left_leg, right_leg (pants / bottoms & footwear)
- 4: belt (waist accessories anchored cleanly to hip joint)
- 5: undershirt (inner top tucked/layered above pants/belt)
- 6: head (head base, ears, facial hair), eyes (6.1), mouth (6.2)
- 7: ear_accessory (earrings / AirPods anchored directly to ear coordinate center)
- 8: front_hair (unified hair silhouette with clipped/masked curls & texture)
- 9: left_arm, right_arm (positioned at shoulder sockets with upward wrist overlap)
- 10: jacket_sleeve_left, jacket_sleeve_right (render OVER arms and match arm angle)
- 11: jacket_front_flaps (framing inner shirt WITHOUT covering arms/hands)
"""
from __future__ import annotations

import math
from pathlib import Path
from typing import List, Sequence, Tuple
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

SS = 4
RIG_W, RIG_H = 400, 500
CW, CH = RIG_W * SS, RIG_H * SS

CHAR_ROOT = Path(__file__).resolve().parent.parent / "assets" / "characters"
JIN_DIR = CHAR_ROOT / "jin"
MEDAZIZ_DIR = CHAR_ROOT / "medazizwerghi"

Point = Tuple[float, float]
RGBA = Tuple[int, int, int, int]

# Canonical Shared Coordinate Anchors (Zero-Gap Sockets)
HEAD_ANCHOR = (200.0, 140.0)
NECK_ANCHOR = (200.0, 204.0)
SHOULDER_LEFT = (130.0, 215.0)
SHOULDER_RIGHT = (270.0, 215.0)
HIP_ANCHOR = (200.0, 310.0)
HIP_LEFT = (165.0, 315.0)
HIP_RIGHT = (235.0, 315.0)
EAR_LEFT = (152.0, 144.0)
EAR_RIGHT = (248.0, 144.0)
HAND_SOCKET_LEFT = (110.0, 305.0)
HAND_SOCKET_RIGHT = (290.0, 305.0)

OUTLINE_WIDTH = 2.5
DETAIL_WIDTH = 1.8


def s(x: float, y: float) -> Point:
    return (x * SS, y * SS)


def sw(width: float) -> int:
    return max(1, int(round(width * SS)))


def cubic_bezier(p0: Point, p1: Point, p2: Point, p3: Point, steps: int = 36) -> List[Point]:
    pts: List[Point] = []
    for i in range(steps + 1):
        t = i / steps
        mt = 1.0 - t
        x = mt**3 * p0[0] + 3 * mt**2 * t * p1[0] + 3 * mt * t**2 * p2[0] + t**3 * p3[0]
        y = mt**3 * p0[1] + 3 * mt**2 * t * p1[1] + 3 * mt * t**2 * p2[1] + t**3 * p3[1]
        pts.append((x, y))
    return pts


def poly_bezier(segments: Sequence[Tuple[Point, Point, Point, Point]], steps: int = 32) -> List[Point]:
    all_pts: List[Point] = []
    for idx, (p0, p1, p2, p3) in enumerate(segments):
        seg = cubic_bezier(s(*p0), s(*p1), s(*p2), s(*p3), steps=steps)
        all_pts.extend(seg if idx == 0 else seg[1:])
    return all_pts


def fill_vertical_gradient(
    target: Image.Image,
    mask_poly: Sequence[Point],
    top_color: RGBA,
    bottom_color: RGBA,
    y_min: float,
    y_max: float,
) -> None:
    mask = Image.new("L", (CW, CH), 0)
    ImageDraw.Draw(mask).polygon(mask_poly, fill=255)

    arr_mask = np.array(mask)
    if not np.any(arr_mask > 0):
        return

    y0 = max(0, int(math.floor(y_min * SS)))
    y1 = min(CH - 1, int(math.ceil(y_max * SS)))
    span = max(1, y1 - y0)

    grad_rows = np.linspace(0.0, 1.0, span + 1)[:, None, None]
    c0 = np.array(top_color, dtype=np.float32)
    c1 = np.array(bottom_color, dtype=np.float32)
    strip = (c0 * (1.0 - grad_rows) + c1 * grad_rows).astype(np.uint8)

    patch_arr = np.zeros((CH, CW, 4), dtype=np.uint8)
    patch_arr[y0 : y1 + 1, :, :] = strip
    patch_arr[:, :, 3] = (patch_arr[:, :, 3].astype(np.float32) * (arr_mask / 255.0)).astype(np.uint8)
    target.alpha_composite(Image.fromarray(patch_arr))


def stroke_smooth_line(draw: ImageDraw.ImageDraw, pts: Sequence[Point], color: RGBA, width: float) -> None:
    w = sw(width)
    draw.line(list(pts), fill=color, width=w, joint="curve")
    r = w / 2.0
    if len(pts) >= 2 and r > 1.5:
        for px, py in (pts[0], pts[-1]):
            draw.ellipse([px - r, py - r, px + r, py + r], fill=color)


def save_layer(canvas: Image.Image, out_dir: Path, filename: str) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    final = canvas.resize((RIG_W, RIG_H), Image.Resampling.LANCZOS)
    final.save(out_dir / filename, format="PNG")


# ===========================================================================
# 1. CHARACTER: JIN (`jin`)
# Archetype: Dark aesthetic manhwa protagonist, black hoodie, glowing cyan eyes
# ===========================================================================
JIN_INK: RGBA = (18, 20, 26, 255)
JIN_SKIN_TOP: RGBA = (248, 224, 210, 255)
JIN_SKIN_BOT: RGBA = (234, 198, 180, 255)
JIN_SKIN_SHADOW: RGBA = (206, 162, 140, 255)

JIN_HOODIE_TOP: RGBA = (36, 40, 52, 255)
JIN_HOODIE_BOT: RGBA = (20, 22, 30, 255)
JIN_HOODIE_LINING: RGBA = (14, 15, 20, 255)
JIN_HOODIE_HIGHLIGHT: RGBA = (60, 68, 88, 255)

JIN_TEE_TOP: RGBA = (48, 54, 66, 255)
JIN_TEE_BOT: RGBA = (32, 36, 46, 255)

JIN_HAIR_TOP: RGBA = (44, 48, 64, 255)
JIN_HAIR_BOT: RGBA = (22, 24, 32, 255)

JIN_PANTS_TOP: RGBA = (34, 38, 48, 255)
JIN_PANTS_BOT: RGBA = (20, 22, 30, 255)

JIN_TEAL: RGBA = (0, 200, 220, 255)
JIN_TEAL_DARK: RGBA = (0, 130, 150, 255)


def build_jin_back_hair() -> None:
    """Z=0: Back hair contour framing the head from behind."""
    canvas = Image.new("RGBA", (CW, CH), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)

    back_poly = poly_bezier([
        ((142, 130), (130, 155), (132, 180), (148, 198)),
        ((148, 198), (160, 208), (175, 214), (200, 214)),
        ((200, 214), (225, 214), (240, 208), (252, 198)),
        ((252, 198), (268, 180), (270, 155), (258, 130)),
        ((258, 130), (240, 95), (160, 95), (142, 130)),
    ])
    fill_vertical_gradient(canvas, back_poly, JIN_HAIR_TOP, JIN_HAIR_BOT, 95, 214)
    stroke_smooth_line(draw, back_poly, JIN_INK, OUTLINE_WIDTH)
    save_layer(canvas, JIN_DIR, "back_hair.png")


def build_jin_jacket_back() -> None:
    """Z=1: Inside lining of the jacket visible behind the inner shirt."""
    canvas = Image.new("RGBA", (CW, CH), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)

    # Wide coverage spanning past outer torso seams (X: 122 to 278)
    lining_poly = poly_bezier([
        ((122, 214), (165, 204), (235, 204), (278, 214)),
        ((278, 214), (270, 260), (266, 310), (262, 345)),
        ((262, 345), (230, 350), (170, 350), (138, 345)),
        ((138, 345), (134, 310), (130, 260), (122, 214)),
    ])
    fill_vertical_gradient(canvas, lining_poly, JIN_HOODIE_LINING, (10, 11, 15, 255), 204, 350)
    stroke_smooth_line(draw, lining_poly, JIN_INK, OUTLINE_WIDTH)
    save_layer(canvas, JIN_DIR, "jacket_back.png")


def build_jin_base_body() -> None:
    """Z=2: Base body with full shoulder corners and a solid pelvis/crotch bridge."""
    canvas = Image.new("RGBA", (CW, CH), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)

    # 1. Neck (overlapping under chin at Y=188)
    neck_poly = poly_bezier([
        ((176, 180), (177, 195), (175, 212), (168, 222)),
        ((168, 222), (184, 228), (216, 228), (232, 222)),
        ((232, 222), (225, 212), (223, 195), (224, 180)),
        ((224, 180), (200, 178), (176, 180), (176, 180)),
    ])
    fill_vertical_gradient(canvas, neck_poly, JIN_SKIN_SHADOW, JIN_SKIN_TOP, 178, 228)
    stroke_smooth_line(draw, [s(176, 180), s(175, 212), s(168, 222)], (45, 30, 25, 255), DETAIL_WIDTH)
    stroke_smooth_line(draw, [s(224, 180), s(225, 212), s(232, 222)], (45, 30, 25, 255), DETAIL_WIDTH)

    # 2. Torso base with shoulders extending fully to X=124 and X=276 + Solid Pelvis Bridge
    torso_and_pelvis = poly_bezier([
        ((124, 214), (165, 204), (235, 204), (276, 214)),
        ((276, 214), (268, 260), (262, 305), (264, 345)),
        ((264, 345), (242, 352), (218, 350), (200, 346)),  # Crotch inseam
        ((200, 346), (182, 350), (158, 352), (136, 345)),  # Pelvis bridge
        ((136, 345), (138, 305), (132, 260), (124, 214)),
    ])
    fill_vertical_gradient(canvas, torso_and_pelvis, (220, 185, 170, 255), (195, 155, 138, 255), 204, 352)
    stroke_smooth_line(draw, torso_and_pelvis, JIN_INK, OUTLINE_WIDTH)

    save_layer(canvas, JIN_DIR, "body.png")


def _build_jin_leg(is_left: bool) -> Image.Image:
    canvas = Image.new("RGBA", (CW, CH), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)

    hx, _ = HIP_LEFT if is_left else HIP_RIGHT
    dx = -12 if is_left else 12

    # Upper thigh extends upward to Y=300 (overlapping 10px into pelvis & under belt)
    leg_poly = poly_bezier([
        ((hx - 22, 300), (hx + 22, 300), (hx + 20 + dx, 360), (hx + 18 + dx, 410)),
        ((hx + 18 + dx, 410), (hx + 16 + dx, 452), (hx - 14 + dx, 452), (hx - 16 + dx, 410)),
        ((hx - 16 + dx, 410), (hx - 18 + dx, 360), (hx - 22, 300), (hx - 22, 300)),
    ])
    fill_vertical_gradient(canvas, leg_poly, JIN_PANTS_TOP, JIN_PANTS_BOT, 300, 452)
    stroke_smooth_line(draw, leg_poly, JIN_INK, OUTLINE_WIDTH)

    # Cargo pocket on thigh
    strap_x = hx - 17 if is_left else hx + 5
    draw.rounded_rectangle([s(strap_x, 345), s(strap_x + 14, 378)], radius=sw(2), fill=(26, 28, 38, 255), outline=JIN_INK, width=sw(DETAIL_WIDTH))
    stroke_smooth_line(draw, [s(strap_x + 7, 378), s(strap_x + 7, 396)], (18, 20, 26, 255), DETAIL_WIDTH)

    # Elastic jogger cuff at Y=440..452 (overlaps shoe collar by 10px)
    draw.rounded_rectangle([s(hx - 15 + dx, 440), s(hx + 17 + dx, 452)], radius=sw(3), fill=(18, 20, 26, 255), outline=JIN_INK, width=sw(OUTLINE_WIDTH))

    # Sneaker collar starts at Y=442 (tucked 10px under cuff)
    shoe_poly = poly_bezier([
        ((hx - 16 + dx, 442), (hx + 18 + dx, 442), (hx + 24 + dx, 465), (hx + 22 + dx, 484)),
        ((hx + 22 + dx, 484), (hx - 18 + dx, 484), (hx - 22 + dx, 470), (hx - 16 + dx, 442)),
    ])
    fill_vertical_gradient(canvas, shoe_poly, JIN_TEAL, JIN_TEAL_DARK, 442, 484)
    stroke_smooth_line(draw, shoe_poly, JIN_INK, OUTLINE_WIDTH)
    # White sole
    draw.rounded_rectangle([s(hx - 22 + dx, 478), s(hx + 24 + dx, 485)], radius=sw(2), fill=(235, 240, 245, 255), outline=JIN_INK, width=sw(DETAIL_WIDTH))

    return canvas


def build_jin_legs() -> None:
    """Z=3: Animated legs / pants & footwear with zero ankle gaps."""
    save_layer(_build_jin_leg(True), JIN_DIR, "left_leg.png")
    save_layer(_build_jin_leg(False), JIN_DIR, "right_leg.png")


def build_jin_belt() -> None:
    """Z=4: Tactical belt spanning X in [136, 264] covering the hip rotation seam."""
    canvas = Image.new("RGBA", (CW, CH), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)

    belt_rect = [s(136, 304), s(264, 320)]
    draw.rounded_rectangle(belt_rect, radius=sw(3), fill=(24, 26, 34, 255), outline=JIN_INK, width=sw(OUTLINE_WIDTH))
    # Chrome buckle at center (200, 312)
    draw.rounded_rectangle([s(188, 302), s(212, 322)], radius=sw(3), fill=(180, 190, 205, 255), outline=JIN_INK, width=sw(OUTLINE_WIDTH))
    draw.rounded_rectangle([s(194, 307), s(206, 317)], radius=sw(2), fill=(40, 45, 55, 255))

    save_layer(canvas, JIN_DIR, "belt.png")


def build_jin_undershirt() -> None:
    """Z=5: Inner top (crewneck tee) tucked cleanly above pants/belt."""
    canvas = Image.new("RGBA", (CW, CH), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)

    tee_poly = poly_bezier([
        ((166, 204), (180, 202), (220, 202), (234, 204)),
        ((234, 204), (256, 250), (252, 290), (248, 318)),
        ((248, 318), (220, 318), (180, 318), (152, 318)),
        ((152, 318), (148, 290), (144, 250), (166, 204)),
    ])
    fill_vertical_gradient(canvas, tee_poly, JIN_TEE_TOP, JIN_TEE_BOT, 202, 318)
    stroke_smooth_line(draw, tee_poly, JIN_INK, OUTLINE_WIDTH)

    # Ribbed collar
    collar = poly_bezier([
        ((170, 206), (182, 220), (218, 220), (230, 206)),
        ((230, 206), (220, 202), (180, 202), (170, 206)),
    ])
    draw.polygon(collar, fill=(35, 40, 50, 255), outline=JIN_INK, width=sw(DETAIL_WIDTH))

    save_layer(canvas, JIN_DIR, "undershirt.png")


def build_jin_head_base() -> None:
    """Z=6: Head base, jawline, ears, nose, eyebrows."""
    canvas = Image.new("RGBA", (CW, CH), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)

    # Cranium & Jaw
    head_poly = poly_bezier([
        ((152, 130), (145, 148), (155, 172), (182, 188)),
        ((182, 188), (194, 194), (206, 194), (218, 188)),
        ((218, 188), (245, 172), (255, 148), (248, 130)),
        ((248, 130), (248, 100), (225, 80), (200, 80)),
        ((200, 80), (175, 80), (152, 100), (152, 130)),
    ])
    fill_vertical_gradient(canvas, head_poly, JIN_SKIN_TOP, JIN_SKIN_BOT, 80, 194)
    stroke_smooth_line(draw, head_poly, JIN_INK, OUTLINE_WIDTH)

    # Ears (Left at (152, 144), Right at (248, 144))
    for ex, is_l in ((EAR_LEFT[0], True), (EAR_RIGHT[0], False)):
        sign = -1 if is_l else 1
        ear_pts = poly_bezier([
            ((ex, 132), (ex + sign * 14, 136), (ex + sign * 14, 154), (ex, 158)),
            ((ex, 158), (ex + sign * 4, 145), (ex, 132), (ex, 132)),
        ])
        fill_vertical_gradient(canvas, ear_pts, JIN_SKIN_TOP, JIN_SKIN_SHADOW, 132, 158)
        stroke_smooth_line(draw, ear_pts, JIN_INK, OUTLINE_WIDTH)

    # Anime nose
    stroke_smooth_line(draw, [s(198, 162), s(200, 168), s(195, 170)], (70, 48, 42, 255), DETAIL_WIDTH)

    # Eyebrows
    stroke_smooth_line(draw, [s(162, 134), s(174, 132), s(186, 135)], JIN_INK, OUTLINE_WIDTH)
    stroke_smooth_line(draw, [s(214, 135), s(226, 132), s(238, 134)], JIN_INK, OUTLINE_WIDTH)

    save_layer(canvas, JIN_DIR, "head.png")


def build_jin_ear_accessory() -> None:
    """Z=7: Ear accessories anchored to EAR_LEFT (152, 144)."""
    canvas = Image.new("RGBA", (CW, CH), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)

    # Silver stud on left earlobe
    draw.ellipse([s(150, 154), s(154, 158)], fill=(220, 230, 245, 255), outline=JIN_INK, width=sw(1.2))

    save_layer(canvas, JIN_DIR, "ear_accessory.png")


def build_jin_front_hair() -> None:
    """Z=8: Front hair & bangs with texture clipped inside the eroded fill mask."""
    canvas = Image.new("RGBA", (CW, CH), (0, 0, 0, 0))

    # 1. Main hair volume polygon
    hair_poly = poly_bezier([
        ((145, 128), (140, 105), (160, 78), (200, 75)),
        ((200, 75), (240, 78), (260, 105), (255, 128)),
        ((255, 128), (248, 136), (240, 122), (232, 138)),
        ((232, 138), (220, 146), (212, 132), (202, 148)),
        ((202, 148), (192, 134), (180, 148), (170, 134)),
        ((170, 134), (160, 142), (152, 124), (145, 128)),
    ])
    fill_vertical_gradient(canvas, hair_poly, JIN_HAIR_TOP, JIN_HAIR_BOT, 75, 148)

    # 2. Texture clipped strictly inside eroded mask (no outer stroke bleed)
    mask = Image.new("L", (CW, CH), 0)
    ImageDraw.Draw(mask).polygon(hair_poly, fill=255)
    mask_inner = mask.filter(ImageFilter.MinFilter(size=sw(OUTLINE_WIDTH) * 2 + 1))

    strand_layer = Image.new("RGBA", (CW, CH), (0, 0, 0, 0))
    strand_draw = ImageDraw.Draw(strand_layer)
    stroke_smooth_line(strand_draw, [s(176, 92), s(182, 118), s(180, 142)], (65, 72, 95, 255), DETAIL_WIDTH)
    stroke_smooth_line(strand_draw, [s(210, 90), s(216, 116), s(212, 142)], (65, 72, 95, 255), DETAIL_WIDTH)

    arr_mask = np.array(mask_inner)
    arr_strand = np.array(strand_layer)
    arr_strand[:, :, 3] = (arr_strand[:, :, 3].astype(np.float32) * (arr_mask / 255.0)).astype(np.uint8)
    canvas.alpha_composite(Image.fromarray(arr_strand))

    # 3. Outer crisp outline
    stroke_smooth_line(ImageDraw.Draw(canvas), hair_poly, JIN_INK, OUTLINE_WIDTH)

    save_layer(canvas, JIN_DIR, "front_hair.png")


def _draw_anime_hand(
    canvas: Image.Image,
    hx: float,
    hy: float,
    is_left: bool,
    skin_top: RGBA,
    skin_bot: RGBA,
    skin_shadow: RGBA,
    ink_color: RGBA,
) -> None:
    """Draw a fully articulated, anatomically sound 5-finger anime hand with zero-gap overlap."""
    draw = ImageDraw.Draw(canvas)
    # is_left: thumb is on inner side (towards torso, sign_in = +1), pinky on outer side
    sign_in = 1.0 if is_left else -1.0

    # 1. Coordinates: wrist stem tucked under cuff (hy - 14) down to fingertips (hy + 38)
    w_top_out = (hx - sign_in * 8, hy - 14)
    w_top_in = (hx + sign_in * 8, hy - 14)
    w_bot_in = (hx + sign_in * 9, hy + 2)

    # Thumb: angled inward and forward
    th_base = (hx + sign_in * 10, hy + 6)
    th_knuckle = (hx + sign_in * 17, hy + 12)
    th_tip = (hx + sign_in * 16, hy + 22)
    th_inner = (hx + sign_in * 11, hy + 20)
    th_web = (hx + sign_in * 7, hy + 14)

    # 4 Articulated Fingers (natural relaxed anime pose)
    # Index finger
    idx_knuckle = (hx + sign_in * 6, hy + 16)
    idx_tip = (hx + sign_in * 4.5, hy + 35)
    idx_inner = (hx + sign_in * 2.0, hy + 34)

    # Middle finger (longest)
    mid_tip = (hx + sign_in * 0.0, hy + 38)
    mid_inner = (hx - sign_in * 2.5, hy + 35)

    # Ring finger
    ring_tip = (hx - sign_in * 4.5, hy + 34)
    ring_inner = (hx - sign_in * 6.5, hy + 31)

    # Pinky finger
    pinky_tip = (hx - sign_in * 8.5, hy + 27)
    pinky_base = (hx - sign_in * 9.5, hy + 16)
    w_bot_out = (hx - sign_in * 8.5, hy + 2)

    # Full hand contour as bezier segments
    hand_poly = poly_bezier([
        (w_top_out, (w_top_out[0], hy - 6), (w_bot_out[0], hy - 2), w_bot_out),
        (w_bot_out, (w_bot_out[0] - sign_in * 2, hy + 10), (pinky_base[0], pinky_base[1] - 2), pinky_base),
        # Pinky
        (pinky_base, (pinky_base[0], pinky_base[1] + 6), (pinky_tip[0] - sign_in * 1, pinky_tip[1] - 3), pinky_tip),
        (pinky_tip, (pinky_tip[0] + sign_in * 1, pinky_tip[1] + 1), (ring_inner[0] - sign_in * 1, ring_inner[1] + 2), ring_inner),
        # Ring
        (ring_inner, (ring_inner[0], ring_inner[1] + 4), (ring_tip[0] - sign_in * 0.5, ring_tip[1] - 2), ring_tip),
        (ring_tip, (ring_tip[0] + sign_in * 1, ring_tip[1] + 1), (mid_inner[0] - sign_in * 0.5, mid_inner[1] + 2), mid_inner),
        # Middle
        (mid_inner, (mid_inner[0], mid_inner[1] + 4), (mid_tip[0] - sign_in * 0.5, mid_tip[1] - 2), mid_tip),
        (mid_tip, (mid_tip[0] + sign_in * 1, mid_tip[1] + 1), (idx_inner[0] - sign_in * 0.5, idx_inner[1] + 2), idx_inner),
        # Index
        (idx_inner, (idx_inner[0], idx_inner[1] + 3), (idx_tip[0] - sign_in * 0.5, idx_tip[1] - 2), idx_tip),
        (idx_tip, (idx_tip[0] + sign_in * 1.5, idx_tip[1] + 1), (idx_knuckle[0], idx_knuckle[1] + 4), idx_knuckle),
        # Webbing to thumb
        (idx_knuckle, (idx_knuckle[0], idx_knuckle[1] - 2), (th_web[0] - sign_in * 1, th_web[1]), th_web),
        (th_web, (th_web[0] + sign_in * 2, th_web[1] + 4), (th_inner[0] - sign_in * 1, th_inner[1] - 1), th_inner),
        # Thumb
        (th_inner, (th_inner[0] + sign_in * 2, th_inner[1] + 2), (th_tip[0] + sign_in * 1, th_tip[1] + 1), th_tip),
        (th_tip, (th_tip[0] + sign_in * 2, th_tip[1] - 3), (th_knuckle[0] + sign_in * 1, th_knuckle[1] + 1), th_knuckle),
        (th_knuckle, (th_knuckle[0], th_knuckle[1] - 4), (th_base[0] + sign_in * 1, th_base[1] + 2), th_base),
        # Up to wrist inner
        (th_base, (th_base[0] - sign_in * 1, th_base[1] - 3), (w_bot_in[0], w_bot_in[1] + 3), w_bot_in),
        (w_bot_in, (w_bot_in[0], hy - 2), (w_top_in[0], hy - 6), w_top_in),
        (w_top_in, (hx, hy - 14), (hx, hy - 14), w_top_out),
    ])

    # Fill skin gradient
    fill_vertical_gradient(canvas, hand_poly, skin_top, skin_bot, hy - 14, hy + 38)

    # Cel shadow under palm / thenar web
    shadow_poly = poly_bezier([
        ((hx - sign_in * 3, hy + 12), (hx + sign_in * 2, hy + 14), (hx + sign_in * 6, hy + 14), th_web),
        (th_web, (hx + sign_in * 4, hy + 20), (hx - sign_in * 2, hy + 22), (hx - sign_in * 3, hy + 12)),
    ])
    draw.polygon(shadow_poly, fill=skin_shadow)

    # Outer outline
    stroke_smooth_line(draw, hand_poly, ink_color, OUTLINE_WIDTH)

    # Finger separation lines inside hand
    stroke_smooth_line(draw, [s(ring_inner[0], ring_inner[1]), s(ring_inner[0] - sign_in * 0.5, ring_inner[1] - 10)], ink_color, DETAIL_WIDTH)
    stroke_smooth_line(draw, [s(mid_inner[0], mid_inner[1]), s(mid_inner[0] - sign_in * 0.5, mid_inner[1] - 14)], ink_color, DETAIL_WIDTH)
    stroke_smooth_line(draw, [s(idx_inner[0], idx_inner[1]), s(idx_inner[0] + sign_in * 0.5, idx_inner[1] - 14)], ink_color, DETAIL_WIDTH)

    # Knuckle creases & palm life line
    stroke_smooth_line(draw, [s(hx + sign_in * 13, hy + 16), s(hx + sign_in * 15, hy + 15)], ink_color, DETAIL_WIDTH)
    stroke_smooth_line(draw, [s(hx + sign_in * 4, hy + 24), s(hx + sign_in * 6, hy + 24)], ink_color, DETAIL_WIDTH)
    stroke_smooth_line(draw, [s(hx - sign_in * 1, hy + 25), s(hx + sign_in * 1, hy + 25)], ink_color, DETAIL_WIDTH)
    stroke_smooth_line(draw, [s(hx - sign_in * 6, hy + 23), s(hx - sign_in * 4, hy + 23)], ink_color, DETAIL_WIDTH)
    stroke_smooth_line(draw, [s(hx + sign_in * 4, hy + 12), s(hx + sign_in * 1, hy + 18), s(hx - sign_in * 4, hy + 15)], skin_shadow, DETAIL_WIDTH)


def _draw_jin_sleeve_mesh(canvas: Image.Image, draw: ImageDraw.ImageDraw, sx: float, sy: float, hx: float, hy: float, is_left: bool) -> None:
    """Draw the techwear hoodie sleeve with elbow folds, creases, and ribbed cuff."""
    sign = -1 if is_left else 1

    # Shoulder cap centered at (sx, sy) radius 20px, extending 24px into torso
    sleeve_poly = poly_bezier([
        ((sx - 20, sy), (sx - 14, sy - 20), (sx + 14, sy - 20), (sx + 20, sy)),
        ((sx + 20, sy), (sx + 16, sy + 25), (hx + sign * 14, hy - 45), (hx + sign * 15, hy - 25)),
        ((hx + sign * 15, hy - 25), (hx + sign * 16, hy - 14), (hx + sign * 13, hy - 2), (hx - sign * 13, hy - 2)),
        ((hx - sign * 13, hy - 2), (hx - sign * 16, hy - 15), (hx - sign * 18, hy - 35), (sx - 18, sy + 30)),
        ((sx - 18, sy + 30), (sx - 22, sy + 15), (sx - 20, sy), (sx - 20, sy)),
    ])
    fill_vertical_gradient(canvas, sleeve_poly, JIN_HOODIE_TOP, JIN_HOODIE_BOT, sy - 20, hy - 2)
    stroke_smooth_line(draw, sleeve_poly, JIN_INK, OUTLINE_WIDTH)

    # Dynamic cloth folds on hoodie sleeve
    fold_color = (18, 20, 28, 255)
    high_color = JIN_HOODIE_HIGHLIGHT
    stroke_smooth_line(draw, [s(sx - sign * 4, sy + 42), s(sx + sign * 6, sy + 48), s(sx - sign * 2, sy + 54)], fold_color, DETAIL_WIDTH)
    stroke_smooth_line(draw, [s(sx - sign * 2, sy + 44), s(sx + sign * 8, sy + 50)], high_color, DETAIL_WIDTH)
    stroke_smooth_line(draw, [s(hx - sign * 6, hy - 22), s(hx + sign * 4, hy - 18)], fold_color, DETAIL_WIDTH)
    stroke_smooth_line(draw, [s(hx - sign * 8, hy - 14), s(hx + sign * 2, hy - 10)], fold_color, DETAIL_WIDTH)

    # Ribbed Elastic Wrist Cuff at hy - 14 .. hy - 2
    cuff_rect = [s(hx - 14, hy - 14), s(hx + 14, hy - 2)]
    draw.rounded_rectangle(cuff_rect, radius=sw(3.5), fill=(26, 28, 38, 255), outline=JIN_INK, width=sw(OUTLINE_WIDTH))
    for rx in (-8, -3, 2, 7):
        stroke_smooth_line(draw, [s(hx + rx, hy - 13), s(hx + rx, hy - 3)], (40, 44, 58, 255), 1.2)


def _build_jin_arm(is_left: bool) -> Image.Image:
    """Z=9: Complete finished anime arm (hoodie sleeve + cuff + articulated 5-finger anime hand)."""
    canvas = Image.new("RGBA", (CW, CH), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)

    sx, sy = SHOULDER_LEFT if is_left else SHOULDER_RIGHT
    hx, hy = HAND_SOCKET_LEFT if is_left else HAND_SOCKET_RIGHT

    # 1. Articulated anime hand (wrist stem tucked under cuff)
    _draw_anime_hand(canvas, hx, hy, is_left, JIN_SKIN_TOP, JIN_SKIN_BOT, JIN_SKIN_SHADOW, JIN_INK)

    # 2. Hoodie sleeve & cuff
    _draw_jin_sleeve_mesh(canvas, draw, sx, sy, hx, hy, is_left)

    return canvas


def build_jin_arms() -> None:
    """Z=9: Arms & hands positioned at shoulder sockets with upward wrist overlap."""
    save_layer(_build_jin_arm(True), JIN_DIR, "left_arm.png")
    save_layer(_build_jin_arm(False), JIN_DIR, "right_arm.png")


def _build_jin_sleeve(is_left: bool) -> Image.Image:
    """Z=10: Outerwear jacket sleeve matching arm silhouette flush into torso."""
    canvas = Image.new("RGBA", (CW, CH), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)

    sx, sy = SHOULDER_LEFT if is_left else SHOULDER_RIGHT
    hx, hy = HAND_SOCKET_LEFT if is_left else HAND_SOCKET_RIGHT

    _draw_jin_sleeve_mesh(canvas, draw, sx, sy, hx, hy, is_left)

    return canvas


def build_jin_sleeves() -> None:
    """Z=10: Jacket sleeves with shoulder caps overlapping flush inside torso corners."""
    save_layer(_build_jin_sleeve(True), JIN_DIR, "jacket_sleeve_left.png")
    save_layer(_build_jin_sleeve(False), JIN_DIR, "jacket_sleeve_right.png")


def build_jin_jacket_front_flaps() -> None:
    """Z=11: Front panels framing inner shirt without covering arms."""
    canvas = Image.new("RGBA", (CW, CH), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)

    # Left front flap: extends from collar (X=174) out to shoulder seam (X=124) down to hem
    left_flap = poly_bezier([
        ((124, 214), (160, 206), (174, 214), (172, 270)),
        ((172, 270), (170, 315), (166, 345), (136, 345)),
        ((136, 345), (134, 305), (130, 260), (124, 214)),
    ])
    fill_vertical_gradient(canvas, left_flap, JIN_HOODIE_TOP, JIN_HOODIE_BOT, 206, 345)
    stroke_smooth_line(draw, left_flap, JIN_INK, OUTLINE_WIDTH)

    # Right front flap: extends from collar (X=226) out to shoulder seam (X=276) down to hem
    right_flap = poly_bezier([
        ((276, 214), (240, 206), (226, 214), (228, 270)),
        ((228, 270), (230, 315), (234, 345), (264, 345)),
        ((264, 345), (266, 305), (270, 260), (276, 214)),
    ])
    fill_vertical_gradient(canvas, right_flap, JIN_HOODIE_TOP, JIN_HOODIE_BOT, 206, 345)
    stroke_smooth_line(draw, right_flap, JIN_INK, OUTLINE_WIDTH)

    # Hood cowl collar around neck
    cowl = poly_bezier([
        ((132, 216), (168, 204), (232, 204), (268, 216)),
        ((268, 216), (258, 228), (222, 222), (200, 224)),
        ((200, 224), (178, 222), (142, 228), (132, 216)),
    ])
    fill_vertical_gradient(canvas, cowl, JIN_HOODIE_HIGHLIGHT, JIN_HOODIE_BOT, 204, 228)
    stroke_smooth_line(draw, cowl, JIN_INK, OUTLINE_WIDTH)

    # Drawstrings
    stroke_smooth_line(draw, [s(176, 218), s(174, 252), s(175, 276)], (200, 210, 225, 255), DETAIL_WIDTH)
    draw.ellipse([s(173, 274), s(177, 280)], fill=(150, 160, 180, 255))
    stroke_smooth_line(draw, [s(224, 218), s(226, 252), s(225, 276)], (200, 210, 225, 255), DETAIL_WIDTH)
    draw.ellipse([s(223, 274), s(227, 280)], fill=(150, 160, 180, 255))

    save_layer(canvas, JIN_DIR, "jacket_front_flaps.png")


# ===========================================================================
# 2. CHARACTER: MEDAZIZ WERGHI (`medazizwerghi`)
# Archetype: Curly fade, refined full beard with sideburns & mustache, AirPod
# ===========================================================================
MED_INK: RGBA = (20, 20, 28, 255)
MED_SKIN_TOP: RGBA = (244, 208, 188, 255)
MED_SKIN_BOT: RGBA = (226, 182, 158, 255)
MED_SKIN_SHADOW: RGBA = (196, 148, 124, 255)

MED_JACKET_PURPLE_TOP: RGBA = (124, 62, 178, 255)
MED_JACKET_PURPLE_BOT: RGBA = (82, 36, 128, 255)
MED_JACKET_BLACK: RGBA = (32, 34, 44, 255)
MED_JACKET_LINING: RGBA = (24, 18, 36, 255)

MED_HAIR_BASE: RGBA = (26, 22, 28, 255)
MED_HAIR_HIGHLIGHT: RGBA = (62, 52, 68, 255)

MED_PANTS_TOP: RGBA = (36, 38, 48, 255)
MED_PANTS_BOT: RGBA = (22, 24, 32, 255)


def build_medaziz_back_hair() -> None:
    """Z=0: Back hair contour at the nape and behind ears."""
    canvas = Image.new("RGBA", (CW, CH), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)

    back_poly = poly_bezier([
        ((144, 126), (134, 150), (138, 175), (152, 192)),
        ((152, 192), (165, 202), (180, 208), (200, 208)),
        ((200, 208), (220, 208), (235, 202), (248, 192)),
        ((248, 192), (262, 175), (266, 150), (256, 126)),
        ((256, 126), (240, 90), (160, 90), (144, 126)),
    ])
    fill_vertical_gradient(canvas, back_poly, MED_HAIR_BASE, (15, 12, 18, 255), 90, 208)
    stroke_smooth_line(draw, back_poly, MED_INK, OUTLINE_WIDTH)
    save_layer(canvas, MEDAZIZ_DIR, "back_hair.png")


def build_medaziz_jacket_back() -> None:
    """Z=1: Inside lining of the jacket visible behind the inner shirt."""
    canvas = Image.new("RGBA", (CW, CH), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)

    lining_poly = poly_bezier([
        ((122, 214), (165, 204), (235, 204), (278, 214)),
        ((278, 214), (270, 260), (266, 310), (262, 345)),
        ((262, 345), (230, 350), (170, 350), (138, 345)),
        ((138, 345), (134, 310), (130, 260), (122, 214)),
    ])
    fill_vertical_gradient(canvas, lining_poly, MED_JACKET_LINING, (14, 10, 22, 255), 204, 350)
    stroke_smooth_line(draw, lining_poly, MED_INK, OUTLINE_WIDTH)
    save_layer(canvas, MEDAZIZ_DIR, "jacket_back.png")


def build_medaziz_base_body() -> None:
    """Z=2: Base body with full shoulder corners and solid pelvis/crotch bridge."""
    canvas = Image.new("RGBA", (CW, CH), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)

    # 1. Neck
    neck_poly = poly_bezier([
        ((176, 180), (177, 195), (175, 212), (168, 222)),
        ((168, 222), (184, 228), (216, 228), (232, 222)),
        ((232, 222), (225, 212), (223, 195), (224, 180)),
        ((224, 180), (200, 178), (176, 180), (176, 180)),
    ])
    fill_vertical_gradient(canvas, neck_poly, MED_SKIN_SHADOW, MED_SKIN_TOP, 178, 228)
    stroke_smooth_line(draw, [s(176, 180), s(175, 212), s(168, 222)], (50, 35, 30, 255), DETAIL_WIDTH)
    stroke_smooth_line(draw, [s(224, 180), s(225, 212), s(232, 222)], (50, 35, 30, 255), DETAIL_WIDTH)

    # 2. Torso base + Solid Pelvis Bridge (connecting left and right thighs with ZERO GAP)
    torso_and_pelvis = poly_bezier([
        ((124, 214), (165, 204), (235, 204), (276, 214)),
        ((276, 214), (268, 260), (262, 305), (264, 345)),
        ((264, 345), (242, 352), (218, 350), (200, 346)),  # Crotch inseam
        ((200, 346), (182, 350), (158, 352), (136, 345)),  # Solid bridge
        ((136, 345), (138, 305), (132, 260), (124, 214)),
    ])
    fill_vertical_gradient(canvas, torso_and_pelvis, (215, 175, 150, 255), (190, 145, 125, 255), 204, 352)
    stroke_smooth_line(draw, torso_and_pelvis, MED_INK, OUTLINE_WIDTH)

    save_layer(canvas, MEDAZIZ_DIR, "body.png")


def _build_medaziz_leg(is_left: bool) -> Image.Image:
    canvas = Image.new("RGBA", (CW, CH), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)

    hx, _ = HIP_LEFT if is_left else HIP_RIGHT
    dx = -12 if is_left else 12

    # Upper thigh extends upward to Y=300 (overlapping 10px into pelvis & under belt)
    leg_poly = poly_bezier([
        ((hx - 22, 300), (hx + 22, 300), (hx + 20 + dx, 360), (hx + 18 + dx, 410)),
        ((hx + 18 + dx, 410), (hx + 16 + dx, 452), (hx - 14 + dx, 452), (hx - 16 + dx, 410)),
        ((hx - 16 + dx, 410), (hx - 18 + dx, 360), (hx - 22, 300), (hx - 22, 300)),
    ])
    fill_vertical_gradient(canvas, leg_poly, MED_PANTS_TOP, MED_PANTS_BOT, 300, 452)
    stroke_smooth_line(draw, leg_poly, MED_INK, OUTLINE_WIDTH)

    # Cargo pocket with purple pull tab
    pocket_x = hx - 17 if is_left else hx + 5
    draw.rounded_rectangle([s(pocket_x, 345), s(pocket_x + 14, 378)], radius=sw(2), fill=(28, 30, 40, 255), outline=MED_INK, width=sw(DETAIL_WIDTH))
    draw.rounded_rectangle([s(pocket_x + 4, 376), s(pocket_x + 10, 388)], radius=sw(1), fill=MED_JACKET_PURPLE_TOP)

    # Ankle jogger cuff at Y=440..452 (overlaps shoe collar by 10px)
    draw.rounded_rectangle([s(hx - 15 + dx, 440), s(hx + 17 + dx, 452)], radius=sw(3), fill=(18, 20, 26, 255), outline=MED_INK, width=sw(OUTLINE_WIDTH))

    # Sneaker collar starts at Y=442 (tucked 10px under cuff)
    shoe_poly = poly_bezier([
        ((hx - 16 + dx, 442), (hx + 18 + dx, 442), (hx + 24 + dx, 465), (hx + 22 + dx, 484)),
        ((hx + 22 + dx, 484), (hx - 18 + dx, 484), (hx - 22 + dx, 470), (hx - 16 + dx, 442)),
    ])
    fill_vertical_gradient(canvas, shoe_poly, MED_JACKET_PURPLE_TOP, MED_JACKET_PURPLE_BOT, 442, 484)
    stroke_smooth_line(draw, shoe_poly, MED_INK, OUTLINE_WIDTH)
    # White sole
    draw.rounded_rectangle([s(hx - 22 + dx, 478), s(hx + 24 + dx, 485)], radius=sw(2), fill=(240, 242, 248, 255), outline=MED_INK, width=sw(DETAIL_WIDTH))

    return canvas


def build_medaziz_legs() -> None:
    """Z=3: Animated legs / pants & footwear with zero ankle gaps."""
    save_layer(_build_medaziz_leg(True), MEDAZIZ_DIR, "left_leg.png")
    save_layer(_build_medaziz_leg(False), MEDAZIZ_DIR, "right_leg.png")


def build_medaziz_belt() -> None:
    """Z=4: Waistband / tactical belt anchored across HIP_ANCHOR (200, 310)."""
    canvas = Image.new("RGBA", (CW, CH), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)

    belt_rect = [s(136, 304), s(264, 320)]
    draw.rounded_rectangle(belt_rect, radius=sw(3), fill=(26, 28, 36, 255), outline=MED_INK, width=sw(OUTLINE_WIDTH))
    # Quick-release tactical buckle at center
    draw.rounded_rectangle([s(188, 302), s(212, 322)], radius=sw(3), fill=(60, 64, 80, 255), outline=MED_INK, width=sw(OUTLINE_WIDTH))
    draw.rounded_rectangle([s(194, 307), s(206, 317)], radius=sw(2), fill=(124, 62, 178, 255))

    save_layer(canvas, MEDAZIZ_DIR, "belt.png")


def build_medaziz_undershirt() -> None:
    """Z=5: Inner graphic tee tucked cleanly above pants/belt."""
    canvas = Image.new("RGBA", (CW, CH), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)

    tee_poly = poly_bezier([
        ((166, 204), (180, 202), (220, 202), (234, 204)),
        ((234, 204), (256, 250), (252, 290), (248, 318)),
        ((248, 318), (220, 318), (180, 318), (152, 318)),
        ((152, 318), (148, 290), (144, 250), (166, 204)),
    ])
    fill_vertical_gradient(canvas, tee_poly, (44, 46, 56, 255), (28, 30, 38, 255), 202, 318)
    stroke_smooth_line(draw, tee_poly, MED_INK, OUTLINE_WIDTH)

    # Crewneck collar
    collar = poly_bezier([
        ((170, 206), (182, 220), (218, 220), (230, 206)),
        ((230, 206), (220, 202), (180, 202), (170, 206)),
    ])
    draw.polygon(collar, fill=(32, 34, 44, 255), outline=MED_INK, width=sw(DETAIL_WIDTH))

    # Graphic emblem print on chest
    graphic_poly = [s(190, 240), s(210, 240), s(215, 270), s(185, 270)]
    draw.polygon(graphic_poly, fill=(80, 70, 95, 255))
    stroke_smooth_line(draw, [s(186, 255), s(214, 255)], (160, 110, 220, 255), DETAIL_WIDTH)

    save_layer(canvas, MEDAZIZ_DIR, "undershirt.png")


def build_medaziz_head_base() -> None:
    """Z=6: Head base with naturally blended full beard, sideburns, and mustache."""
    canvas = Image.new("RGBA", (CW, CH), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)

    # 1. Cranium & Jaw base
    head_poly = poly_bezier([
        ((152, 130), (145, 148), (155, 172), (182, 188)),
        ((182, 188), (194, 194), (206, 194), (218, 188)),
        ((218, 188), (245, 172), (255, 148), (248, 130)),
        ((248, 130), (248, 100), (225, 80), (200, 80)),
        ((200, 80), (175, 80), (152, 100), (152, 130)),
    ])
    fill_vertical_gradient(canvas, head_poly, MED_SKIN_TOP, MED_SKIN_BOT, 80, 194)
    stroke_smooth_line(draw, head_poly, MED_INK, OUTLINE_WIDTH)

    # 2. Ears (Left at (152, 144), Right at (248, 144))
    for ex, is_l in ((EAR_LEFT[0], True), (EAR_RIGHT[0], False)):
        sign = -1 if is_l else 1
        ear_pts = poly_bezier([
            ((ex, 132), (ex + sign * 14, 136), (ex + sign * 14, 154), (ex, 158)),
            ((ex, 158), (ex + sign * 4, 145), (ex, 132), (ex, 132)),
        ])
        fill_vertical_gradient(canvas, ear_pts, MED_SKIN_TOP, MED_SKIN_SHADOW, 132, 158)
        stroke_smooth_line(draw, ear_pts, MED_INK, OUTLINE_WIDTH)

    # 3. Refined full beard smoothly tapered to sideburns & mustache (NOT a chin-strap outline!)
    beard_poly = poly_bezier([
        # Sideburn starting right at left ear base (150, 138)
        ((150, 138), (152, 160), (160, 178), (180, 192)),
        ((180, 192), (194, 196), (206, 196), (220, 192)),
        # Sweeping up to right sideburn at ear base (250, 138)
        ((220, 192), (240, 178), (248, 160), (250, 138)),
        ((250, 138), (242, 150), (236, 165), (224, 174)),
        # Mustache bridging across upper lip (168..176) framing mouth
        ((224, 174), (216, 172), (200, 170), (184, 172)),
        ((184, 172), (176, 174), (164, 165), (158, 150)),
        ((158, 150), (150, 138), (150, 138), (150, 138)),
    ])
    fill_vertical_gradient(canvas, beard_poly, (36, 32, 42, 255), (18, 15, 22, 255), 138, 196)
    stroke_smooth_line(draw, beard_poly, MED_INK, OUTLINE_WIDTH)

    # Mustache definition stroke
    stroke_smooth_line(draw, [s(186, 173), s(200, 171), s(214, 173)], (18, 15, 22, 255), DETAIL_WIDTH)

    # Anime nose
    stroke_smooth_line(draw, [s(198, 162), s(200, 168), s(195, 170)], (75, 50, 45, 255), DETAIL_WIDTH)

    # Eyebrows
    stroke_smooth_line(draw, [s(162, 134), s(174, 131), s(186, 134)], MED_INK, OUTLINE_WIDTH)
    stroke_smooth_line(draw, [s(214, 134), s(226, 131), s(238, 134)], MED_INK, OUTLINE_WIDTH)

    save_layer(canvas, MEDAZIZ_DIR, "head.png")


def build_medaziz_ear_accessory() -> None:
    """Z=7: White Apple AirPod anchored directly to EAR_RIGHT (248, 144)."""
    canvas = Image.new("RGBA", (CW, CH), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)

    ear_x, ear_y = EAR_RIGHT
    draw.ellipse([s(ear_x - 3, ear_y - 2), s(ear_x + 5, ear_y + 6)], fill=(250, 252, 255, 255), outline=MED_INK, width=sw(1.2))
    stroke_smooth_line(draw, [s(ear_x + 1, ear_y + 5), s(ear_x + 2, ear_y + 18)], (245, 248, 255, 255), 2.2)
    draw.ellipse([s(ear_x, ear_y + 16), s(ear_x + 4, ear_y + 19)], fill=(180, 190, 205, 255))

    save_layer(canvas, MEDAZIZ_DIR, "ear_accessory.png")


def build_medaziz_front_hair() -> None:
    """Z=8: Front hair & curly fade silhouette with texture strictly clipped inside eroded fill path."""
    canvas = Image.new("RGBA", (CW, CH), (0, 0, 0, 0))

    # 1. Main hair volume polygon
    hair_poly = poly_bezier([
        ((148, 130), (142, 102), (160, 72), (200, 70)),
        ((200, 70), (240, 72), (258, 102), (252, 130)),
        ((252, 130), (246, 120), (236, 126), (226, 116)),
        ((226, 116), (216, 124), (204, 114), (196, 124)),
        ((196, 124), (184, 114), (174, 124), (164, 116)),
        ((164, 116), (154, 124), (148, 130), (148, 130)),
    ])
    fill_vertical_gradient(canvas, hair_poly, MED_HAIR_HIGHLIGHT, MED_HAIR_BASE, 70, 130)

    # 2. Curl textures STRICTLY CLIPPED inside eroded fill mask (excluding stroke)
    mask = Image.new("L", (CW, CH), 0)
    ImageDraw.Draw(mask).polygon(hair_poly, fill=255)
    mask_inner = mask.filter(ImageFilter.MinFilter(size=sw(OUTLINE_WIDTH) * 2 + 1))

    curl_layer = Image.new("RGBA", (CW, CH), (0, 0, 0, 0))
    curl_draw = ImageDraw.Draw(curl_layer)
    for cx, cy, r in (
        (175, 88, 7), (195, 82, 8), (215, 86, 7), (230, 95, 6),
        (165, 102, 6), (185, 98, 7), (205, 98, 7), (225, 106, 6),
        (175, 114, 6), (195, 112, 6), (215, 114, 6),
    ):
        stroke_smooth_line(curl_draw, [s(cx - r, cy), s(cx, cy - r), s(cx + r, cy), s(cx, cy + r)], (50, 42, 58, 200), DETAIL_WIDTH)

    arr_mask = np.array(mask_inner)
    arr_curl = np.array(curl_layer)
    arr_curl[:, :, 3] = (arr_curl[:, :, 3].astype(np.float32) * (arr_mask / 255.0)).astype(np.uint8)
    canvas.alpha_composite(Image.fromarray(arr_curl))

    # 3. Outer crisp outline
    stroke_smooth_line(ImageDraw.Draw(canvas), hair_poly, MED_INK, OUTLINE_WIDTH)

    save_layer(canvas, MEDAZIZ_DIR, "front_hair.png")


def _draw_medaziz_sleeve_mesh(canvas: Image.Image, draw: ImageDraw.ImageDraw, sx: float, sy: float, hx: float, hy: float, is_left: bool) -> None:
    """Draw the two-tone purple & black techwear windbreaker sleeve with tactical cargo pocket."""
    sign = -1 if is_left else 1

    # Purple sleeve base with shoulder cap extending 24px into torso
    sleeve_poly = poly_bezier([
        ((sx - 20, sy), (sx - 14, sy - 20), (sx + 14, sy - 20), (sx + 20, sy)),
        ((sx + 20, sy), (sx + 16, sy + 25), (hx + sign * 14, hy - 45), (hx + sign * 15, hy - 25)),
        ((hx + sign * 15, hy - 25), (hx + sign * 16, hy - 14), (hx + sign * 13, hy - 2), (hx - sign * 13, hy - 2)),
        ((hx - sign * 13, hy - 2), (hx - sign * 16, hy - 15), (hx - sign * 18, hy - 35), (sx - 18, sy + 30)),
        ((sx - 18, sy + 30), (sx - 22, sy + 15), (sx - 20, sy), (sx - 20, sy)),
    ])
    fill_vertical_gradient(canvas, sleeve_poly, MED_JACKET_PURPLE_TOP, MED_JACKET_PURPLE_BOT, sy - 20, hy - 2)
    stroke_smooth_line(draw, sleeve_poly, MED_INK, OUTLINE_WIDTH)

    # Black shoulder yoke at top of sleeve
    yoke_poly = poly_bezier([
        ((sx - 20, sy), (sx - 14, sy - 20), (sx + 14, sy - 20), (sx + 20, sy)),
        ((sx + 20, sy), (sx + 18, sy + 24), (sx - 18, sy + 24), (sx - 20, sy)),
    ])
    draw.polygon(yoke_poly, fill=MED_JACKET_BLACK, outline=MED_INK, width=sw(OUTLINE_WIDTH))
    stroke_smooth_line(draw, [s(sx - 18, sy + 24), s(sx + 18, sy + 24)], (160, 90, 230, 255), 1.5)

    # Outer black stripe running down sleeve
    stripe_poly = poly_bezier([
        ((sx - sign * 18, sy + 24), (sx - sign * 12, sy + 24), (hx - sign * 10, hy - 14), (hx - sign * 15, hy - 14)),
        ((hx - sign * 15, hy - 14), (hx - sign * 17, hy - 28), (sx - sign * 21, sy + 32), (sx - sign * 18, sy + 24)),
    ])
    draw.polygon(stripe_poly, fill=(24, 25, 34, 255), outline=MED_INK, width=sw(1.2))

    # Tactical bicep cargo pocket on sleeve
    px = sx - sign * 3
    py = sy + 35
    pocket_rect = [s(px - 9, py), s(px + 9, py + 22)]
    draw.rounded_rectangle(pocket_rect, radius=sw(2.5), fill=(32, 34, 46, 255), outline=MED_INK, width=sw(OUTLINE_WIDTH))
    flap_rect = [s(px - 10, py - 2), s(px + 10, py + 7)]
    draw.rounded_rectangle(flap_rect, radius=sw(2), fill=(22, 23, 30, 255), outline=MED_INK, width=sw(OUTLINE_WIDTH))
    draw.rounded_rectangle([s(px - 2.5, py + 4), s(px + 2.5, py + 16)], radius=sw(1), fill=(140, 75, 205, 255))
    draw.rounded_rectangle([s(px - 4, py + 9), s(px + 4, py + 12)], radius=sw(1), outline=MED_INK, width=sw(1.2))

    # Ribbed wrist cuff at hy - 14 .. hy - 2
    cuff_rect = [s(hx - 14, hy - 14), s(hx + 14, hy - 2)]
    draw.rounded_rectangle(cuff_rect, radius=sw(3.5), fill=(24, 26, 36, 255), outline=MED_INK, width=sw(OUTLINE_WIDTH))
    for rx in (-8, -3, 2, 7):
        stroke_smooth_line(draw, [s(hx + rx, hy - 13), s(hx + rx, hy - 3)], (45, 48, 62, 255), 1.2)


def _build_medaziz_arm(is_left: bool) -> Image.Image:
    """Z=9: Complete finished anime arm (windbreaker sleeve + cargo pocket + cuff + anime hand)."""
    canvas = Image.new("RGBA", (CW, CH), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)

    sx, sy = SHOULDER_LEFT if is_left else SHOULDER_RIGHT
    hx, hy = HAND_SOCKET_LEFT if is_left else HAND_SOCKET_RIGHT

    # 1. Articulated anime hand (wrist stem tucked under cuff)
    _draw_anime_hand(canvas, hx, hy, is_left, MED_SKIN_TOP, MED_SKIN_BOT, MED_SKIN_SHADOW, MED_INK)

    # 2. Techwear windbreaker sleeve & cuff
    _draw_medaziz_sleeve_mesh(canvas, draw, sx, sy, hx, hy, is_left)

    return canvas


def build_medaziz_arms() -> None:
    """Z=9: Arms & hands positioned at shoulder sockets with upward wrist overlap."""
    save_layer(_build_medaziz_arm(True), MEDAZIZ_DIR, "left_arm.png")
    save_layer(_build_medaziz_arm(False), MEDAZIZ_DIR, "right_arm.png")


def _build_medaziz_sleeve(is_left: bool) -> Image.Image:
    """Z=10: Outerwear jacket sleeve matching arm silhouette flush into torso."""
    canvas = Image.new("RGBA", (CW, CH), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)

    sx, sy = SHOULDER_LEFT if is_left else SHOULDER_RIGHT
    hx, hy = HAND_SOCKET_LEFT if is_left else HAND_SOCKET_RIGHT

    _draw_medaziz_sleeve_mesh(canvas, draw, sx, sy, hx, hy, is_left)

    return canvas


def build_medaziz_sleeves() -> None:
    """Z=10: Jacket sleeves with shoulder caps overlapping flush inside torso corners."""
    save_layer(_build_medaziz_sleeve(True), MEDAZIZ_DIR, "jacket_sleeve_left.png")
    save_layer(_build_medaziz_sleeve(False), MEDAZIZ_DIR, "jacket_sleeve_right.png")


def build_medaziz_jacket_front_flaps() -> None:
    """Z=11: Front panels framing inner shirt without covering arms."""
    canvas = Image.new("RGBA", (CW, CH), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)

    # Left front flap: extends from collar (X=174) out to shoulder seam (X=124) down to hem
    left_flap = poly_bezier([
        ((124, 214), (160, 206), (174, 214), (172, 270)),
        ((172, 270), (170, 315), (166, 345), (136, 345)),
        ((136, 345), (134, 305), (130, 260), (124, 214)),
    ])
    fill_vertical_gradient(canvas, left_flap, MED_JACKET_PURPLE_TOP, MED_JACKET_PURPLE_BOT, 206, 345)
    stroke_smooth_line(draw, left_flap, MED_INK, OUTLINE_WIDTH)

    # Black chest yoke on left flap
    left_yoke = poly_bezier([
        ((124, 214), (160, 206), (174, 214), (173, 245)),
        ((173, 245), (131, 245), (124, 214), (124, 214)),
    ])
    draw.polygon(left_yoke, fill=MED_JACKET_BLACK, outline=MED_INK, width=sw(OUTLINE_WIDTH))

    # Right front flap: extends from collar (X=226) out to shoulder seam (X=276) down to hem
    right_flap = poly_bezier([
        ((276, 214), (240, 206), (226, 214), (228, 270)),
        ((228, 270), (230, 315), (234, 345), (264, 345)),
        ((264, 345), (266, 305), (270, 260), (276, 214)),
    ])
    fill_vertical_gradient(canvas, right_flap, MED_JACKET_PURPLE_TOP, MED_JACKET_PURPLE_BOT, 206, 345)
    stroke_smooth_line(draw, right_flap, MED_INK, OUTLINE_WIDTH)

    # Black chest yoke on right flap
    right_yoke = poly_bezier([
        ((276, 214), (240, 206), (226, 214), (227, 245)),
        ((227, 245), (269, 245), (276, 214), (276, 214)),
    ])
    draw.polygon(right_yoke, fill=MED_JACKET_BLACK, outline=MED_INK, width=sw(OUTLINE_WIDTH))

    # Tech collar stand
    collar = poly_bezier([
        ((132, 216), (168, 204), (232, 204), (268, 216)),
        ((268, 216), (258, 226), (222, 220), (200, 222)),
        ((200, 222), (178, 220), (142, 226), (132, 216)),
    ])
    fill_vertical_gradient(canvas, collar, (50, 52, 66, 255), (24, 26, 36, 255), 204, 226)
    stroke_smooth_line(draw, collar, MED_INK, OUTLINE_WIDTH)

    save_layer(canvas, MEDAZIZ_DIR, "jacket_front_flaps.png")


# ===========================================================================
# 3. EXPRESSIONS: EYES & MOUTHS (SHARED RIG SOCKETS)
# Sockets: Eyes at (174, 144) and (226, 144); Mouth at (200, 182)
# ===========================================================================
def _render_eye(
    draw: ImageDraw.ImageDraw,
    cx: float,
    cy: float,
    style: str,
    glow_color: RGBA,
    ink_color: RGBA,
) -> None:
    if style == "closed":
        stroke_smooth_line(draw, [s(cx - 14, cy + 2), s(cx, cy + 6), s(cx + 14, cy + 2)], ink_color, OUTLINE_WIDTH)
    elif style == "angry":
        stroke_smooth_line(draw, [s(cx - 14, cy - 2), s(cx, cy - 5), s(cx + 14, cy - 2)], ink_color, OUTLINE_WIDTH)
        draw.ellipse([s(cx - 10, cy - 6), s(cx + 10, cy + 6)], fill=(255, 255, 255, 255))
        draw.ellipse([s(cx - 6, cy - 4), s(cx + 6, cy + 6)], fill=glow_color)
        draw.ellipse([s(cx - 3, cy - 2), s(cx + 3, cy + 4)], fill=ink_color)
    elif style == "shocked":
        draw.ellipse([s(cx - 14, cy - 10), s(cx + 14, cy + 10)], fill=(255, 255, 255, 255), outline=ink_color, width=sw(OUTLINE_WIDTH))
        draw.ellipse([s(cx - 5, cy - 5), s(cx + 5, cy + 5)], fill=glow_color)
        draw.ellipse([s(cx - 2, cy - 2), s(cx + 2, cy + 2)], fill=ink_color)
    else:  # open
        stroke_smooth_line(draw, [s(cx - 14, cy - 3), s(cx, cy - 7), s(cx + 14, cy - 3)], ink_color, OUTLINE_WIDTH)
        draw.ellipse([s(cx - 11, cy - 6), s(cx + 11, cy + 7)], fill=(255, 255, 255, 255))
        draw.ellipse([s(cx - 7, cy - 4), s(cx + 7, cy + 7)], fill=glow_color)
        draw.ellipse([s(cx - 3, cy - 2), s(cx + 3, cy + 4)], fill=ink_color)
        # Specular glint
        draw.ellipse([s(cx - 4, cy - 3), s(cx - 1, cy)], fill=(255, 255, 255, 255))
        stroke_smooth_line(draw, [s(cx - 10, cy + 8), s(cx + 10, cy + 8)], ink_color, DETAIL_WIDTH)


def build_character_eyes(out_dir: Path, glow_color: RGBA, ink_color: RGBA) -> None:
    for style in ("open", "closed", "angry", "shocked"):
        canvas = Image.new("RGBA", (CW, CH), (0, 0, 0, 0))
        draw = ImageDraw.Draw(canvas)
        _render_eye(draw, 174.0, 144.0, style, glow_color, ink_color)
        _render_eye(draw, 226.0, 144.0, style, glow_color, ink_color)
        save_layer(canvas, out_dir, f"eyes_{style}.png")


def build_character_mouths(out_dir: Path, ink_color: RGBA) -> None:
    mouths = {
        "neutral": lambda d: stroke_smooth_line(d, [s(190, 182), s(200, 183), s(210, 182)], ink_color, OUTLINE_WIDTH),
        "happy": lambda d: (
            d.polygon(poly_bezier([
                ((188, 180), (200, 180), (212, 180), (212, 180)),
                ((212, 180), (210, 192), (190, 192), (188, 180)),
            ]), fill=(185, 45, 60, 255), outline=ink_color),
            d.polygon([s(192, 180), s(208, 180), s(208, 184), s(192, 184)], fill=(255, 255, 255, 255)),
            stroke_smooth_line(d, [s(188, 180), s(200, 181), s(212, 180)], ink_color, OUTLINE_WIDTH),
        ),
        "smirk": lambda d: stroke_smooth_line(d, [s(190, 184), s(202, 183), s(214, 177)], ink_color, OUTLINE_WIDTH),
        "sad": lambda d: stroke_smooth_line(d, [s(190, 185), s(200, 181), s(210, 185)], ink_color, OUTLINE_WIDTH),
        "angry": lambda d: stroke_smooth_line(d, [s(188, 186), s(200, 182), s(212, 186)], ink_color, OUTLINE_WIDTH),
        "surprised": lambda d: d.ellipse([s(194, 178), s(206, 190)], fill=(160, 40, 50, 255), outline=ink_color, width=sw(OUTLINE_WIDTH)),
        "shocked": lambda d: d.ellipse([s(192, 175), s(208, 193)], fill=(140, 30, 40, 255), outline=ink_color, width=sw(OUTLINE_WIDTH)),
    }

    for name, draw_fn in mouths.items():
        canvas = Image.new("RGBA", (CW, CH), (0, 0, 0, 0))
        draw_fn(ImageDraw.Draw(canvas))
        save_layer(canvas, out_dir, f"mouth_{name}.png")


def main() -> None:
    print("Generating zero-gap modular character rigs with strict Z-index layering...")

    # Jin
    build_jin_back_hair()
    build_jin_jacket_back()
    build_jin_base_body()
    build_jin_legs()
    build_jin_belt()
    build_jin_undershirt()
    build_jin_head_base()
    build_jin_ear_accessory()
    build_jin_front_hair()
    build_jin_arms()
    build_jin_sleeves()
    build_jin_jacket_front_flaps()
    build_character_eyes(JIN_DIR, JIN_TEAL, JIN_INK)
    build_character_mouths(JIN_DIR, JIN_INK)
    print("-> Jin generated with zero-gap overlap.")

    # MedAziz Werghi
    build_medaziz_back_hair()
    build_medaziz_jacket_back()
    build_medaziz_base_body()
    build_medaziz_legs()
    build_medaziz_belt()
    build_medaziz_undershirt()
    build_medaziz_head_base()
    build_medaziz_ear_accessory()
    build_medaziz_front_hair()
    build_medaziz_arms()
    build_medaziz_sleeves()
    build_medaziz_jacket_front_flaps()
    build_character_eyes(MEDAZIZ_DIR, (140, 75, 40, 255), MED_INK)
    build_character_mouths(MEDAZIZ_DIR, MED_INK)
    print("-> MedAziz Werghi generated with zero-gap overlap.")

    print("All zero-gap modular character assets built successfully!")


if __name__ == "__main__":
    main()
