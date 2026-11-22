"""Generate a 4x supersampled cel-shaded manhwa RGBA PNG rig for Kim Gong-ja (`gongja`).

Draws smooth cubic Bezier contours, layered anime/manhwa cel-shading gradients,
sculpted hands aligned to AvatarScript prop sockets (82, 330) / (318, 330),
and expressive eyes/mouths on 1600x2000 canvases downsampled via LANCZOS to 400x500.
"""
from __future__ import annotations

from pathlib import Path
from typing import List, Sequence, Tuple
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

SS = 4
RIG_W, RIG_H = 400, 500
CW, CH = RIG_W * SS, RIG_H * SS
OUT_DIR = Path(__file__).resolve().parent.parent / "assets" / "characters" / "gongja"

Point = Tuple[float, float]
RGBA = Tuple[int, int, int, int]


def s(x: float, y: float) -> Point:
    """Scale rig coordinate (400x500) to 4x supersampled canvas (1600x2000)."""
    return (x * SS, y * SS)


def sw(width: float) -> int:
    """Scale stroke width to 4x supersampled pixels."""
    return max(1, int(round(width * SS)))


def cubic_bezier(p0: Point, p1: Point, p2: Point, p3: Point, steps: int = 36) -> List[Point]:
    """Sample points along a cubic Bezier curve."""
    pts: List[Point] = []
    for i in range(steps + 1):
        t = i / steps
        mt = 1.0 - t
        x = (
            mt**3 * p0[0]
            + 3 * mt**2 * t * p1[0]
            + 3 * mt * t**2 * p2[0]
            + t**3 * p3[0]
        )
        y = (
            mt**3 * p0[1]
            + 3 * mt**2 * t * p1[1]
            + 3 * mt * t**2 * p2[1]
            + t**3 * p3[1]
        )
        pts.append((x, y))
    return pts


def poly_bezier(segments: Sequence[Tuple[Point, Point, Point, Point]], steps: int = 32) -> List[Point]:
    """Concatenate chained cubic Bezier segments in rig coordinates, scaled by SS."""
    all_pts: List[Point] = []
    for idx, (p0, p1, p2, p3) in enumerate(segments):
        seg = cubic_bezier(s(*p0), s(*p1), s(*p2), s(*p3), steps=steps)
        all_pts.extend(seg if idx == 0 else seg[1:])
    return all_pts


def composite_masked(base: Image.Image, overlay: Image.Image, mask: Image.Image) -> None:
    """Alpha-composite overlay onto base clipped by mask without erasing existing alpha."""
    arr = np.array(overlay, dtype=np.uint8)
    m = np.array(mask, dtype=np.float32) / 255.0
    arr[:, :, 3] = (arr[:, :, 3].astype(np.float32) * m).astype(np.uint8)
    base.alpha_composite(Image.fromarray(arr))


def fill_vertical_gradient(
    target: Image.Image,
    mask_poly: Sequence[Point],
    top_color: RGBA,
    bottom_color: RGBA,
    y_min: float,
    y_max: float,
) -> None:
    """Fill a polygon region with a smooth vertical RGBA gradient."""
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
    """Draw a smooth anti-aliased multi-point stroke with rounded joints (opaque blend safe)."""
    w = sw(width)
    draw.line(list(pts), fill=color, width=w, joint="curve")
    r = w / 2.0
    if len(pts) >= 2 and r > 1.5:
        for px, py in (pts[0], pts[-1]):
            draw.ellipse([px - r, py - r, px + r, py + r], fill=color)


def draw_soft_blended(base: Image.Image, draw_fn) -> None:
    """Execute translucent ImageDraw calls onto an isolated layer and alpha_composite onto base."""
    layer = new_ss()
    draw_fn(ImageDraw.Draw(layer))
    base.alpha_composite(layer)


def new_ss() -> Image.Image:
    return Image.new("RGBA", (CW, CH), (0, 0, 0, 0))


def save_layer(canvas: Image.Image, filename: str) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    final = canvas.resize((RIG_W, RIG_H), Image.Resampling.LANCZOS)
    final.save(OUT_DIR / filename, format="PNG")


# ---------------------------------------------------------------------------
# Color Palette (Manhwa Kim Gong-ja: dark hunter coat, off-white tee, charcoal hair)
# ---------------------------------------------------------------------------
INK_DARK: RGBA = (12, 14, 22, 255)
INK_HAIR: RGBA = (28, 30, 44, 255)
INK_WARM: RGBA = (48, 30, 26, 255)
SKIN_TOP: RGBA = (246, 217, 198, 255)
SKIN_BOT: RGBA = (232, 194, 172, 255)
SKIN_SHADOW: RGBA = (204, 158, 134, 255)
SKIN_DEEP_SHADOW: RGBA = (176, 128, 106, 255)

SHIRT_TOP: RGBA = (236, 240, 248, 255)
SHIRT_BOT: RGBA = (198, 206, 222, 255)
SHIRT_SHADOW: RGBA = (160, 170, 188, 255)

COAT_TOP: RGBA = (40, 46, 64, 255)
COAT_BOT: RGBA = (22, 26, 38, 255)
COAT_LAPEL: RGBA = (54, 62, 86, 255)
COAT_SHADOW: RGBA = (15, 18, 26, 255)
COAT_HIGHLIGHT: RGBA = (92, 104, 136, 185)

HAIR_MAIN: RGBA = (38, 39, 52, 255)
HAIR_DARK: RGBA = (24, 24, 34, 255)
HAIR_MID: RGBA = (58, 60, 78, 255)
HAIR_SHEEN: RGBA = (116, 120, 152, 205)


def build_body() -> None:
    """Full-body hunter upper torso ending in waist belt & flared coattails over hip sockets."""
    canvas = new_ss()
    draw = ImageDraw.Draw(canvas)

    # 1. Outer Hunter Coat torso & flared hip coattails (waist ~y=360, side tails ~y=404)
    coat_outer = poly_bezier([
        ((102, 256), (132, 244), (168, 242), (200, 244)),
        ((200, 244), (232, 242), (268, 244), (298, 256)),
        ((298, 256), (310, 315), (320, 368), (326, 404)),
        ((326, 404), (294, 408), (266, 396), (254, 372)),
        ((254, 372), (222, 374), (178, 374), (146, 372)),
        ((146, 372), (134, 396), (106, 408), (74, 404)),
        ((74, 404), (80, 368), (90, 315), (102, 256)),
    ])
    fill_vertical_gradient(canvas, coat_outer, COAT_TOP, COAT_BOT, 242, 408)

    # 2. Inner off-white crew-neck T-shirt tucked into hunter waist belt
    shirt_poly = poly_bezier([
        ((154, 248), (176, 244), (224, 244), (246, 248)),
        ((246, 248), (254, 304), (252, 344), (248, 360)),
        ((248, 360), (200, 364), (152, 360), (152, 360)),
        ((152, 360), (148, 344), (146, 304), (154, 248)),
    ])
    fill_vertical_gradient(canvas, shirt_poly, SHIRT_TOP, SHIRT_BOT, 244, 364)

    # Shirt chest shadows & crease folds
    draw.polygon([s(154, 260), s(169, 268), s(163, 358), s(149, 358)], fill=SHIRT_SHADOW)
    draw.polygon([s(246, 260), s(231, 268), s(237, 358), s(251, 358)], fill=SHIRT_SHADOW)
    stroke_smooth_line(draw, [s(182, 305), s(194, 336), s(190, 355)], (178, 186, 204, 255), 2.0)
    stroke_smooth_line(draw, [s(220, 312), s(210, 348)], (178, 186, 204, 255), 1.8)

    # Crew-neck shirt collar ribbing
    collar_rim = poly_bezier([
        ((164, 245), (175, 276), (225, 276), (236, 245)),
        ((236, 245), (224, 238), (176, 238), (164, 245)),
    ])
    draw.polygon(collar_rim, fill=(214, 220, 234, 255), outline=INK_DARK, width=sw(2.8))

    # 3. Coat Left/Right Front Panels, Flared Coattails & Tailored Lapels
    left_panel = poly_bezier([
        ((102, 256), (125, 246), (148, 244), (162, 248)),
        ((162, 248), (168, 300), (160, 356), (146, 376)),
        ((146, 376), (128, 398), (102, 408), (74, 404)),
        ((74, 404), (80, 362), (90, 315), (102, 256)),
    ])
    right_panel = poly_bezier([
        ((298, 256), (275, 246), (252, 244), (238, 248)),
        ((238, 248), (232, 300), (240, 356), (254, 376)),
        ((254, 376), (272, 398), (298, 408), (326, 404)),
        ((326, 404), (320, 362), (310, 315), (298, 256)),
    ])
    fill_vertical_gradient(canvas, left_panel, COAT_TOP, COAT_BOT, 244, 408)
    fill_vertical_gradient(canvas, right_panel, COAT_TOP, COAT_BOT, 244, 408)

    left_lapel = poly_bezier([
        ((130, 250), (148, 244), (162, 248), (166, 256)),
        ((166, 256), (174, 298), (170, 330), (158, 344)),
        ((158, 344), (140, 320), (130, 292), (130, 250)),
    ])
    right_lapel = poly_bezier([
        ((270, 250), (252, 244), (238, 248), (234, 256)),
        ((234, 256), (226, 298), (230, 330), (242, 344)),
        ((242, 344), (260, 320), (270, 292), (270, 250)),
    ])
    draw.polygon(left_lapel, fill=COAT_LAPEL, outline=INK_DARK, width=sw(3.0))
    draw.polygon(right_lapel, fill=COAT_LAPEL, outline=INK_DARK, width=sw(3.0))

    draw.polygon([s(104, 265), s(126, 260), s(112, 404), s(80, 400)], fill=COAT_SHADOW)
    draw.polygon([s(296, 265), s(274, 260), s(288, 404), s(320, 400)], fill=COAT_SHADOW)
    draw_soft_blended(
        canvas,
        lambda d: (
            stroke_smooth_line(d, [s(105, 256), s(144, 248)], COAT_HIGHLIGHT, 2.6),
            stroke_smooth_line(d, [s(295, 256), s(256, 248)], COAT_HIGHLIGHT, 2.6),
        ),
    )

    # Diagonal Hunter Utility Chest Strap + Clasp
    stroke_smooth_line(draw, [s(122, 270), s(248, 360)], (18, 20, 28, 255), 11.5)
    stroke_smooth_line(draw, [s(122, 270), s(248, 360)], (58, 65, 84, 255), 7.2)
    draw.rounded_rectangle([s(176, 306), s(200, 330)], radius=sw(4), fill=(214, 222, 236, 255), outline=INK_DARK, width=sw(2.6))
    draw.rounded_rectangle([s(182, 312), s(194, 324)], radius=sw(2), fill=(72, 80, 98, 255))

    # Waistline Hunter Belt + Trousers Waistband covering hip pivots (162, 372) / (238, 372)
    pelvis_band = poly_bezier([
        ((144, 354), (176, 352), (224, 352), (256, 354)),
        ((256, 354), (262, 368), (258, 380), (248, 384)),
        ((248, 384), (218, 386), (204, 384), (200, 380)),
        ((200, 380), (196, 384), (182, 386), (152, 384)),
        ((152, 384), (142, 380), (138, 368), (144, 354)),
    ])
    fill_vertical_gradient(canvas, pelvis_band, (38, 42, 56, 255), (22, 25, 36, 255), 352, 386)
    stroke_smooth_line(draw, pelvis_band, INK_DARK, 3.0)

    # Leather belt + silver buckle across waist
    draw.rounded_rectangle([s(146, 348), s(254, 366)], radius=sw(4), fill=(24, 26, 36, 255), outline=INK_DARK, width=sw(2.8))
    draw.rounded_rectangle([s(188, 345), s(212, 369)], radius=sw(4), fill=(210, 218, 232, 255), outline=INK_DARK, width=sw(2.8))
    draw.rounded_rectangle([s(194, 351), s(206, 363)], radius=sw(2), fill=(64, 72, 90, 255))

    stroke_smooth_line(draw, coat_outer, INK_DARK, 3.6)
    stroke_smooth_line(draw, [s(164, 255), s(166, 326), s(146, 374)], INK_DARK, 3.0)
    stroke_smooth_line(draw, [s(236, 255), s(234, 326), s(254, 374)], INK_DARK, 3.0)

    # 4. Anatomical Neck & Cast Chin Shadow
    neck_poly = poly_bezier([
        ((176, 206), (177, 228), (175, 246), (170, 252)),
        ((170, 252), (186, 268), (214, 268), (230, 252)),
        ((230, 252), (225, 246), (223, 228), (224, 206)),
        ((224, 206), (200, 204), (176, 206), (176, 206)),
    ])
    fill_vertical_gradient(canvas, neck_poly, SKIN_SHADOW, SKIN_TOP, 206, 268)
    chin_shadow = poly_bezier([
        ((176, 214), (188, 242), (212, 242), (224, 214)),
        ((224, 214), (200, 208), (176, 214), (176, 214)),
    ])
    draw.polygon(chin_shadow, fill=SKIN_DEEP_SHADOW)
    stroke_smooth_line(draw, [s(184, 228), s(194, 254)], (190, 146, 126, 255), 1.8)
    stroke_smooth_line(draw, [s(216, 228), s(206, 254)], (190, 146, 126, 255), 1.8)
    stroke_smooth_line(draw, [s(176, 208), s(175, 248), s(170, 252)], INK_WARM, 2.8)
    stroke_smooth_line(draw, [s(224, 208), s(225, 248), s(230, 252)], INK_WARM, 2.8)

    save_layer(canvas, "body.png")


def _build_right_arm_canvas() -> Image.Image:
    """Build sleek right arm (pivot 305, 265) with bigger sculpted hand at prop socket (318, 330)."""
    canvas = new_ss()
    draw = ImageDraw.Draw(canvas)

    # Tapered coat sleeve stopping at wrist (y=316) so the larger hand stands out boldly
    sleeve_poly = poly_bezier([
        ((286, 256), (299, 253), (313, 258), (323, 274)),
        ((323, 274), (331, 290), (335, 304), (333, 316)),
        ((333, 316), (320, 319), (306, 318), (298, 313)),
        ((298, 313), (292, 292), (288, 274), (286, 256)),
    ])
    fill_vertical_gradient(canvas, sleeve_poly, COAT_TOP, COAT_BOT, 253, 320)
    draw_soft_blended(
        canvas,
        lambda d: stroke_smooth_line(d, [s(321, 274), s(329, 292), s(330, 312)], COAT_HIGHLIGHT, 2.4),
    )
    draw.polygon([s(292, 278), s(308, 286), s(306, 312), s(296, 310)], fill=COAT_SHADOW)

    cuff_poly = [s(297, 304), s(334, 306), s(332, 318), s(299, 316)]
    draw.polygon(cuff_poly, fill=(50, 56, 76, 255), outline=INK_DARK, width=sw(3.0))
    stroke_smooth_line(draw, sleeve_poly, INK_DARK, 3.4)

    # Larger expressive sculpted manhwa hand (~48x54px) centered around socket (318, 332..366)
    wrist_poly = [s(306, 313), s(328, 313), s(330, 326), s(304, 326)]
    draw.polygon(wrist_poly, fill=SKIN_SHADOW)

    # Inner curled palm + distinct articulated fingers + inner thumb crease
    hand_poly = poly_bezier([
        ((304, 316), (294, 324), (292, 340), (298, 353)),
        ((298, 353), (305, 366), (320, 370), (333, 364)),
        ((333, 364), (344, 358), (346, 341), (341, 327)),
        ((341, 327), (337, 319), (328, 316), (318, 316)),
        ((318, 316), (311, 316), (304, 316), (304, 316)),
    ])
    fill_vertical_gradient(canvas, hand_poly, SKIN_TOP, SKIN_BOT, 316, 370)

    # Thumb + inner palm shadow + finger fold dividers
    thumb_shadow = poly_bezier([
        ((297, 327), (309, 335), (313, 346), (308, 356)),
        ((308, 356), (299, 353), (295, 340), (297, 327)),
    ], steps=18)
    draw.polygon(thumb_shadow, fill=SKIN_SHADOW)
    stroke_smooth_line(draw, hand_poly, INK_WARM, 3.2)
    # Prominent thumb fold & curled finger seams
    stroke_smooth_line(draw, [s(304, 326), s(314, 338), s(311, 354)], INK_WARM, 2.4)
    stroke_smooth_line(draw, [s(321, 346), s(320, 366)], (172, 126, 108, 255), 2.2)
    stroke_smooth_line(draw, [s(330, 344), s(329, 364)], (172, 126, 108, 255), 2.2)
    stroke_smooth_line(draw, [s(338, 340), s(337, 358)], (172, 126, 108, 255), 2.0)

    return canvas


def build_arms() -> None:
    right_arm = _build_right_arm_canvas()
    save_layer(right_arm, "right_arm.png")

    left_arm = right_arm.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
    save_layer(left_arm, "left_arm.png")


def _build_right_leg_canvas() -> Image.Image:
    """Build full right leg + combat boot pivoting cleanly around hip (238, 372) down to y=492."""
    canvas = new_ss()
    draw = ImageDraw.Draw(canvas)

    # 1. Hunter Trousers (rounded thigh cap y=354..376 tucked behind body.png pelvis/belt)
    leg_poly = poly_bezier([
        ((216, 358), (230, 350), (250, 352), (260, 366)),
        ((260, 366), (264, 396), (261, 428), (257, 454)),
        ((257, 454), (242, 456), (228, 456), (218, 454)),
        ((218, 454), (214, 426), (213, 392), (216, 358)),
    ])
    fill_vertical_gradient(canvas, leg_poly, (42, 46, 62, 255), (24, 27, 38, 255), 350, 456)

    # Trouser outer fold highlight & knee contour creases
    draw_soft_blended(
        canvas,
        lambda d: stroke_smooth_line(d, [s(254, 372), s(255, 412), s(252, 444)], (84, 94, 124, 175), 2.4),
    )
    draw.polygon([s(216, 376), s(228, 384), s(227, 450), s(217, 450)], fill=(18, 20, 30, 255))
    stroke_smooth_line(draw, [s(228, 414), s(240, 418), s(250, 413)], INK_DARK, 2.0)
    stroke_smooth_line(draw, [s(232, 423), s(244, 421)], (62, 68, 90, 255), 1.6)
    stroke_smooth_line(draw, leg_poly, INK_DARK, 3.4)

    # 2. Combat Hunter Boot (y=444..493, toe angled neatly outward toward x=268)
    boot_poly = poly_bezier([
        ((217, 445), (238, 444), (252, 444), (259, 445)),
        ((259, 445), (261, 462), (266, 474), (272, 482)),
        ((272, 482), (274, 489), (268, 493), (252, 493)),
        ((252, 493), (234, 493), (220, 493), (215, 491)),
        ((215, 491), (213, 478), (216, 462), (217, 445)),
    ])
    fill_vertical_gradient(canvas, boot_poly, (32, 35, 48, 255), (16, 18, 26, 255), 444, 493)

    # Thick lugged combat sole + welt trim
    sole_poly = [s(215, 485), s(273, 485), s(271, 493), s(215, 493)]
    draw.polygon(sole_poly, fill=(11, 13, 19, 255), outline=INK_DARK, width=sw(2.2))
    stroke_smooth_line(draw, [s(216, 484), s(271, 484)], (74, 82, 104, 255), 1.8)

    # Metallic boot straps & shin buckle details
    for strap_y in (454, 465):
        draw.rounded_rectangle(
            [s(217, strap_y), s(260, strap_y + 5)],
            radius=sw(1.5),
            fill=(20, 22, 32, 255),
            outline=INK_DARK,
            width=sw(1.8),
        )
        draw.rounded_rectangle(
            [s(248, strap_y - 0.5), s(255, strap_y + 5.5)],
            radius=sw(1.5),
            fill=(186, 196, 216, 255),
            outline=INK_DARK,
            width=sw(1.2),
        )

    # Toe-cap shine highlight
    draw_soft_blended(
        canvas,
        lambda d: stroke_smooth_line(d, [s(252, 474), s(264, 479)], (102, 112, 142, 185), 2.4),
    )
    stroke_smooth_line(draw, boot_poly, INK_DARK, 3.2)

    return canvas


def build_legs() -> None:
    right_leg = _build_right_leg_canvas()
    save_layer(right_leg, "right_leg.png")

    left_leg = right_leg.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
    save_layer(left_leg, "left_leg.png")


def build_head() -> None:
    canvas = new_ss()
    draw = ImageDraw.Draw(canvas)

    # 1. Tousled Back Raven Hair Silhouette with subtle charcoal-indigo rim visibility
    back_hair = poly_bezier([
        ((100, 152), (82, 118), (86, 68), (118, 38)),
        ((118, 38), (156, 12), (244, 12), (282, 38)),
        ((282, 38), (314, 68), (318, 118), (300, 152)),
        ((300, 152), (296, 188), (274, 212), (254, 214)),
        ((254, 214), (200, 216), (146, 214), (146, 214)),
        ((146, 214), (126, 212), (104, 188), (100, 152)),
    ])
    draw.polygon(back_hair, fill=HAIR_DARK, outline=(52, 56, 78, 255), width=sw(3.2))

    # 2. Ears & black stud piercing
    for side in (-1, 1):
        cx = 200 + side * 86
        ear_poly = poly_bezier([
            ((cx - side * 6, 142), (cx + side * 12, 138), (cx + side * 14, 162), (cx + side * 8, 178)),
            ((cx + side * 8, 178), (cx + side * 2, 188), (cx - side * 8, 184), (cx - side * 10, 168)),
            ((cx - side * 10, 168), (cx - side * 10, 152), (cx - side * 6, 142), (cx - side * 6, 142)),
        ])
        fill_vertical_gradient(canvas, ear_poly, SKIN_TOP, SKIN_SHADOW, 138, 188)
        stroke_smooth_line(draw, ear_poly, INK_WARM, 2.8)
        stroke_smooth_line(
            draw,
            [s(cx + side * 2, 152), s(cx + side * 4, 164), s(cx - side * 1, 172)],
            (186, 142, 122, 255),
            2.0,
        )

    draw.ellipse([s(104, 172), s(114, 182)], fill=(20, 22, 32, 255), outline=(65, 70, 92, 255), width=sw(1.2))
    draw.ellipse([s(106.5, 174), s(109, 176.5)], fill=(235, 240, 255, 255))

    # 3. Sharp tapered manhwa face silhouette (clean bright cel-shaded skin!)
    face_poly = poly_bezier([
        ((118, 138), (116, 102), (146, 74), (200, 74)),
        ((200, 74), (254, 74), (284, 102), (282, 138)),
        ((282, 138), (282, 174), (266, 206), (236, 225)),
        ((236, 225), (214, 237), (186, 237), (164, 225)),
        ((164, 225), (134, 206), (118, 174), (118, 138)),
    ])
    fill_vertical_gradient(canvas, face_poly, SKIN_TOP, SKIN_BOT, 74, 238)

    # Soft jawline cel-shadow & subtle warm rose blush alpha-composited safely
    jaw_left_shade = poly_bezier([
        ((120, 148), (125, 188), (154, 218), (196, 235)),
        ((196, 235), (168, 222), (136, 192), (126, 152)),
        ((126, 152), (120, 148), (120, 148), (120, 148)),
    ])
    draw_soft_blended(
        canvas,
        lambda d: (
            d.polygon(jaw_left_shade, fill=(214, 168, 144, 115)),
            d.ellipse([s(134, 162), s(166, 175)], fill=(240, 174, 164, 58)),
            d.ellipse([s(234, 162), s(266, 175)], fill=(240, 174, 164, 58)),
        ),
    )

    # Soft forehead hair-cast shadow composited WITHOUT erasing skin alpha!
    brow_shadow = new_ss()
    ImageDraw.Draw(brow_shadow).polygon(
        [s(120, 78), s(280, 78), s(278, 114), s(200, 120), s(122, 114)],
        fill=(192, 142, 120, 90),
    )
    brow_shadow = brow_shadow.filter(ImageFilter.GaussianBlur(radius=sw(3.5)))
    face_mask = Image.new("L", (CW, CH), 0)
    ImageDraw.Draw(face_mask).polygon(face_poly, fill=255)
    composite_masked(canvas, brow_shadow, face_mask)

    # Delicate anime nose bridge + nostril shadow
    stroke_smooth_line(draw, [s(200, 147), s(197, 165), s(201, 169)], INK_WARM, 2.2)
    draw.polygon([s(201, 168), s(195, 167), s(198, 173)], fill=(198, 150, 130, 255))

    # Crisp face jawline outline
    stroke_smooth_line(draw, face_poly, INK_WARM, 3.2)

    # 4. Sculpted Tousled Manhwa Hair Crown & Dynamic Spikes
    hair_crown = poly_bezier([
        ((104, 142), (92, 100), (104, 52), (144, 30)),
        ((144, 30), (186, 12), (228, 16), (266, 36)),
        ((266, 36), (300, 58), (306, 104), (296, 142)),
        ((296, 142), (288, 104), (270, 86), (252, 108)),
        ((252, 108), (240, 82), (218, 86), (205, 114)),
        ((205, 114), (192, 86), (170, 84), (154, 112)),
        ((154, 112), (140, 84), (118, 98), (104, 142)),
    ])
    fill_vertical_gradient(canvas, hair_crown, HAIR_MID, HAIR_MAIN, 12, 145)
    stroke_smooth_line(draw, hair_crown, (62, 66, 90, 255), 3.0)

    # Feathered spiky bangs & side locks (keep y=116..158 eyebrows/eyes unobscured!)
    strands = [
        # Left & right cheek side locks
        [((110, 96), (98, 132), (104, 172), (118, 194)), ((118, 194), (120, 160), (120, 126), (126, 96))],
        [((290, 96), (302, 132), (296, 172), (282, 194)), ((282, 194), (280, 160), (280, 126), (274, 96))],
        # Swept bangs above eyebrows + single thin middle lock between eyes
        [((138, 68), (133, 94), (138, 110), (146, 118)), ((146, 118), (150, 104), (152, 86), (156, 68))],
        [((187, 64), (185, 96), (190, 122), (199, 136)), ((199, 136), (203, 114), (205, 90), (205, 64))],
        [((220, 68), (222, 92), (228, 108), (238, 116)), ((238, 116), (242, 100), (242, 84), (240, 68))],
        # Crown messy spiky cowlick tufts
        [((162, 26), (176, 6), (202, 6), (222, 20)), ((222, 20), (204, 20), (182, 24), (162, 26))],
        [((236, 26), (258, 10), (280, 16), (290, 40)), ((290, 40), (272, 32), (252, 30), (236, 26))],
        [((118, 42), (126, 20), (146, 16), (160, 26)), ((160, 26), (144, 30), (130, 36), (118, 42))],
    ]
    for s_left, s_right in strands:
        strand_poly = poly_bezier([s_left, s_right], steps=24)
        draw.polygon(strand_poly, fill=HAIR_MAIN, outline=INK_HAIR, width=sw(2.4))

    # Crisp broken anime hair highlight bands composited safely
    def _draw_hl(d):
        for hx0, hx1, hy in ((130, 178, 52), (190, 248, 48), (256, 282, 58)):
            hl = poly_bezier([
                ((hx0, hy + 7), ((hx0 + hx1) / 2, hy - 8), ((hx0 + hx1) / 2, hy - 8), (hx1, hy + 4)),
                ((hx1, hy + 4), ((hx0 + hx1) / 2, hy - 1), ((hx0 + hx1) / 2, hy - 1), (hx0, hy + 7)),
            ], steps=18)
            d.polygon(hl, fill=HAIR_SHEEN)

    draw_soft_blended(canvas, _draw_hl)

    save_layer(canvas, "head.png")


def _draw_iris_and_sclera(
    canvas: Image.Image,
    cx: float,
    cy: float,
    openness: float = 1.0,
    pupil_scale: float = 1.0,
    iris_glow: int = 0,
    angry: bool = False,
) -> None:
    """Render one crisp white-sclera cel-shaded manhwa eye centered at (cx, cy)."""
    draw = ImageDraw.Draw(canvas)
    side = -1 if cx < 200 else 1

    rx = 18.0
    ry = 14.0 * openness
    sclera_box = [s(cx - rx, cy - ry), s(cx + rx, cy + ry)]
    draw.ellipse(sclera_box, fill=(255, 255, 255, 255))

    # Subtle cool top-eyelid shadow over white sclera
    draw.chord(
        [s(cx - rx, cy - ry - 1), s(cx + rx, cy + ry * 0.25)],
        start=185,
        end=355,
        fill=(220, 226, 238, 255),
    )

    eye_mask = Image.new("L", (CW, CH), 0)
    ImageDraw.Draw(eye_mask).ellipse(sclera_box, fill=255)

    iris_layer = new_ss()
    idraw = ImageDraw.Draw(iris_layer)
    ir = 10.2 * pupil_scale
    idraw.ellipse([s(cx - ir, cy - ir), s(cx + ir, cy + ir)], fill=(38, 16, 22, 255))
    idraw.ellipse(
        [s(cx - ir * 0.80, cy - ir * 0.72), s(cx + ir * 0.80, cy + ir * 0.85)],
        fill=(min(255, 118 + iris_glow), 24, 38, 255),
    )
    idraw.chord(
        [s(cx - ir * 0.68, cy - ir * 0.3), s(cx + ir * 0.68, cy + ir * 0.82)],
        start=10,
        end=170,
        fill=(min(255, 206 + iris_glow), 48, 70, 255),
    )
    pr = 4.6 * pupil_scale
    idraw.ellipse([s(cx - pr, cy - pr), s(cx + pr, cy + pr)], fill=(12, 8, 12, 255))
    idraw.chord([s(cx - ir, cy - ir), s(cx + ir, cy + 2)], start=180, end=360, fill=(20, 12, 18, 130))

    idraw.ellipse([s(cx - ir * 0.52, cy - ir * 0.56), s(cx - ir * 0.14, cy - ir * 0.18)], fill=(255, 255, 255, 250))
    idraw.ellipse([s(cx + ir * 0.25, cy + ir * 0.18), s(cx + ir * 0.48, cy + ir * 0.42)], fill=(255, 255, 255, 225))

    # Composite iris WITHOUT wiping surrounding white sclera!
    composite_masked(canvas, iris_layer, eye_mask)

    upper_pts = cubic_bezier(
        s(cx - side * (rx - 1.5), cy - ry * 0.10 + (4 if angry else 0)),
        s(cx - side * 6, cy - ry * 1.12 + (2 if angry else 0)),
        s(cx + side * 9, cy - ry * 1.08),
        s(cx + side * (rx + 3.5), cy - ry * 0.16 - (2 if angry else 0)),
        steps=24,
    )
    stroke_smooth_line(draw, upper_pts, INK_DARK, 3.6)

    crease_pts = cubic_bezier(
        s(cx - side * 11, cy - ry * 1.25),
        s(cx, cy - ry * 1.46),
        s(cx + side * 12, cy - ry * 1.32),
        s(cx + side * 15, cy - ry * 0.95),
        steps=18,
    )
    stroke_smooth_line(draw, crease_pts, (162, 116, 98, 185), 1.4)

    lower_pts = cubic_bezier(
        s(cx - side * 11, cy + ry * 0.88),
        s(cx, cy + ry * 1.04),
        s(cx + side * 10, cy + ry * 0.95),
        s(cx + side * 15, cy + ry * 0.58),
        steps=18,
    )
    stroke_smooth_line(draw, lower_pts, INK_WARM, 1.8)
    bag_pts = cubic_bezier(
        s(cx - side * 12, cy + ry * 1.25),
        s(cx, cy + ry * 1.42),
        s(cx + side * 10, cy + ry * 1.35),
        s(cx + side * 14, cy + ry * 1.15),
        steps=14,
    )
    stroke_smooth_line(draw, bag_pts, (182, 134, 114, 145), 1.4)


def _draw_brow(draw: ImageDraw.ImageDraw, cx: float, cy: float, mode: str) -> None:
    side = -1 if cx < 200 else 1
    if mode == "angry":
        pts = cubic_bezier(
            s(cx - side * 18, cy + 7),
            s(cx - side * 4, cy + 1),
            s(cx + side * 8, cy - 5),
            s(cx + side * 18, cy - 8),
            steps=18,
        )
    elif mode == "shocked":
        pts = cubic_bezier(
            s(cx - side * 16, cy - 4),
            s(cx - side * 4, cy - 11),
            s(cx + side * 8, cy - 10),
            s(cx + side * 17, cy - 3),
            steps=18,
        )
    else:
        pts = cubic_bezier(
            s(cx - side * 16, cy + 1),
            s(cx - side * 4, cy - 3),
            s(cx + side * 8, cy - 2),
            s(cx + side * 17, cy + 2),
            steps=18,
        )
    stroke_smooth_line(draw, pts, INK_DARK, 3.2)


def build_eyes() -> None:
    # 1. eyes_open.png
    c_open = new_ss()
    _draw_iris_and_sclera(c_open, 162, 144, openness=0.92, pupil_scale=0.96, iris_glow=0)
    _draw_iris_and_sclera(c_open, 238, 144, openness=0.92, pupil_scale=0.96, iris_glow=0)
    d_open = ImageDraw.Draw(c_open)
    _draw_brow(d_open, 162, 120, "normal")
    _draw_brow(d_open, 238, 120, "normal")
    save_layer(c_open, "eyes_open.png")

    # 2. eyes_closed.png
    c_closed = new_ss()
    d_closed = ImageDraw.Draw(c_closed)
    for cx in (162, 238):
        side = -1 if cx < 200 else 1
        lash = cubic_bezier(
            s(cx - side * 16, 143),
            s(cx - side * 4, 152),
            s(cx + side * 8, 152),
            s(cx + side * 18, 142),
            steps=20,
        )
        stroke_smooth_line(d_closed, lash, INK_DARK, 3.6)
        _draw_brow(d_closed, cx, 122, "normal")
    save_layer(c_closed, "eyes_closed.png")

    # 3. eyes_angry.png
    c_angry = new_ss()
    _draw_iris_and_sclera(c_angry, 162, 145, openness=0.76, pupil_scale=0.92, iris_glow=35, angry=True)
    _draw_iris_and_sclera(c_angry, 238, 145, openness=0.76, pupil_scale=0.92, iris_glow=35, angry=True)
    d_angry = ImageDraw.Draw(c_angry)
    _draw_brow(d_angry, 162, 120, "angry")
    _draw_brow(d_angry, 238, 120, "angry")
    stroke_smooth_line(d_angry, [s(194, 118), s(192, 126)], INK_WARM, 1.8)
    stroke_smooth_line(d_angry, [s(206, 118), s(208, 126)], INK_WARM, 1.8)
    save_layer(c_angry, "eyes_angry.png")

    # 4. eyes_shocked.png
    c_shocked = new_ss()
    _draw_iris_and_sclera(c_shocked, 162, 143, openness=1.18, pupil_scale=0.58, iris_glow=55)
    _draw_iris_and_sclera(c_shocked, 238, 143, openness=1.18, pupil_scale=0.58, iris_glow=55)
    d_shocked = ImageDraw.Draw(c_shocked)
    _draw_brow(d_shocked, 162, 114, "shocked")
    _draw_brow(d_shocked, 238, 114, "shocked")
    sweat = poly_bezier([
        ((268, 114), (275, 126), (277, 136), (268, 139)),
        ((268, 139), (259, 136), (261, 126), (268, 114)),
    ], steps=18)
    d_shocked.polygon(sweat, fill=(210, 238, 255, 240), outline=(45, 78, 112, 230), width=sw(2.0))
    d_shocked.ellipse([s(264.5, 128), s(267.5, 134)], fill=(255, 255, 255, 245))
    save_layer(c_shocked, "eyes_shocked.png")


def build_mouths() -> None:
    cx, cy = 200.0, 196.0

    # 1. mouth_neutral.png
    c = new_ss()
    d = ImageDraw.Draw(c)
    pts = cubic_bezier(s(cx - 16, cy + 1), s(cx - 6, cy + 3), s(cx + 6, cy + 3), s(cx + 16, cy), steps=20)
    stroke_smooth_line(d, pts, INK_WARM, 2.8)
    stroke_smooth_line(d, [s(cx - 7, cy + 7), s(cx + 7, cy + 7)], (196, 150, 128, 165), 1.6)
    save_layer(c, "mouth_neutral.png")

    # 2. mouth_smirk.png
    c = new_ss()
    d = ImageDraw.Draw(c)
    pts = cubic_bezier(s(cx - 14, cy + 3), s(cx - 2, cy + 5), s(cx + 10, cy + 1), s(cx + 21, cy - 6), steps=22)
    stroke_smooth_line(d, pts, INK_WARM, 3.0)
    stroke_smooth_line(d, [s(cx + 19, cy - 8), s(cx + 22, cy - 4)], INK_WARM, 2.0)
    stroke_smooth_line(d, [s(cx - 4, cy + 8), s(cx + 8, cy + 7)], (196, 150, 128, 155), 1.5)
    save_layer(c, "mouth_smirk.png")

    # 3. mouth_sad.png
    c = new_ss()
    d = ImageDraw.Draw(c)
    pts = cubic_bezier(s(cx - 15, cy + 7), s(cx - 5, cy - 2), s(cx + 5, cy - 2), s(cx + 15, cy + 7), steps=20)
    stroke_smooth_line(d, pts, INK_WARM, 2.8)
    stroke_smooth_line(d, [s(cx - 5, cy + 9), s(cx + 5, cy + 9)], (196, 150, 128, 155), 1.5)
    save_layer(c, "mouth_sad.png")

    # 4. mouth_happy.png
    c = new_ss()
    d = ImageDraw.Draw(c)
    mouth_box = poly_bezier([
        ((cx - 22, cy - 4), (cx - 8, cy - 1), (cx + 8, cy - 1), (cx + 22, cy - 4)),
        ((cx + 22, cy - 4), (cx + 20, cy + 14), (cx + 8, cy + 18), (cx, cy + 18)),
        ((cx, cy + 18), (cx - 8, cy + 18), (cx - 20, cy + 14), (cx - 22, cy - 4)),
    ], steps=20)
    d.polygon(mouth_box, fill=(92, 24, 34, 255))
    d.ellipse([s(cx - 13, cy + 5), s(cx + 13, cy + 20)], fill=(196, 86, 98, 255))
    d.polygon([s(cx - 20, cy - 4), s(cx + 20, cy - 4), s(cx + 17, cy + 4), s(cx - 17, cy + 4)], fill=(255, 255, 255, 255))
    m_mask = Image.new("L", (CW, CH), 0)
    ImageDraw.Draw(m_mask).polygon(mouth_box, fill=255)
    clipped = new_ss()
    composite_masked(clipped, c, m_mask)
    stroke_smooth_line(ImageDraw.Draw(clipped), mouth_box, INK_WARM, 2.8)
    save_layer(clipped, "mouth_happy.png")

    # 5. mouth_angry.png
    c = new_ss()
    d = ImageDraw.Draw(c)
    snarl = poly_bezier([
        ((cx - 22, cy + 4), (cx - 10, cy - 6), (cx + 10, cy - 6), (cx + 22, cy + 4)),
        ((cx + 22, cy + 4), (cx + 18, cy + 13), (cx + 8, cy + 11), (cx, cy + 10)),
        ((cx, cy + 10), (cx - 8, cy + 11), (cx - 18, cy + 13), (cx - 22, cy + 4)),
    ], steps=18)
    d.polygon(snarl, fill=(252, 252, 255, 255), outline=INK_WARM, width=sw(2.8))
    stroke_smooth_line(d, [s(cx - 18, cy + 3), s(cx, cy + 1), s(cx + 18, cy + 3)], (170, 175, 190, 220), 1.6)
    save_layer(c, "mouth_angry.png")

    # 6. mouth_surprised.png
    c = new_ss()
    d = ImageDraw.Draw(c)
    oval = [s(cx - 11, cy - 4), s(cx + 11, cy + 16)]
    d.ellipse(oval, fill=(84, 22, 34, 255))
    d.ellipse([s(cx - 8, cy + 5), s(cx + 8, cy + 16)], fill=(185, 76, 88, 255))
    m_mask = Image.new("L", (CW, CH), 0)
    ImageDraw.Draw(m_mask).ellipse(oval, fill=255)
    clipped = new_ss()
    composite_masked(clipped, c, m_mask)
    ImageDraw.Draw(clipped).ellipse(oval, outline=INK_WARM, width=sw(2.8))
    save_layer(clipped, "mouth_surprised.png")

    # 7. mouth_shocked.png
    c = new_ss()
    d = ImageDraw.Draw(c)
    shock_box = poly_bezier([
        ((cx - 18, cy - 3), (cx - 12, cy - 11), (cx + 12, cy - 11), (cx + 18, cy - 3)),
        ((cx + 18, cy - 3), (cx + 20, cy + 15), (cx + 12, cy + 26), (cx, cy + 26)),
        ((cx, cy + 26), (cx - 12, cy + 26), (cx - 20, cy + 15), (cx - 18, cy - 3)),
    ], steps=18)
    d.polygon(shock_box, fill=(76, 18, 28, 255))
    d.ellipse([s(cx - 12, cy + 10), s(cx + 12, cy + 25)], fill=(182, 70, 84, 255))
    d.polygon([s(cx - 14, cy - 9), s(cx + 14, cy - 9), s(cx + 12, cy - 1), s(cx - 12, cy - 1)], fill=(255, 255, 255, 255))
    m_mask = Image.new("L", (CW, CH), 0)
    ImageDraw.Draw(m_mask).polygon(shock_box, fill=255)
    clipped = new_ss()
    composite_masked(clipped, c, m_mask)
    stroke_smooth_line(ImageDraw.Draw(clipped), shock_box, INK_WARM, 3.0)
    save_layer(clipped, "mouth_shocked.png")


def main() -> None:
    build_body()
    build_arms()
    build_legs()
    build_head()
    build_eyes()
    build_mouths()
    png_count = len(list(OUT_DIR.glob("*.png")))
    print(f"Generated {png_count} enhanced 400x500 PNG layers in {OUT_DIR}")


if __name__ == "__main__":
    main()
