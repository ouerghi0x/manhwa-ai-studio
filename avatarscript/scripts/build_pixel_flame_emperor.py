"""Pixel Art Character Rig Generator for Flame Emperor (Yoo Soo-ha) in AvatarScript.

Generates a complete 16-bit retro pixel-art character rig on a 100x125 grid,
upscaled 4x with nearest-neighbor point filtering to exact 400x500 RGBA layers:
- body.png
- head.png
- left_arm.png
- right_arm.png
- left_leg.png
- right_leg.png
- eyes_open.png, eyes_closed.png, eyes_angry.png, eyes_shocked.png
- mouth_neutral.png, mouth_smirk.png, mouth_happy.png, mouth_angry.png, mouth_shocked.png, mouth_sad.png, mouth_surprised.png
"""
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from PIL import Image, ImageDraw

GRID_W = 100
GRID_H = 125
SCALE = 4
TARGET_SIZE = (400, 500)

OUT_DIR = Path(__file__).resolve().parent.parent / "assets" / "characters" / "flame_emperor"

# --- PALETTE (Authentic 16-bit Retro RPG / Fighting Game Palette) ---
C_TRANSPARENT = (0, 0, 0, 0)
C_BLACK_OUTLINE = (22, 10, 14, 255)
C_DARK_RED_OUTLINE = (74, 5, 14, 255)

# Skin
C_SKIN_HIGHLIGHT = (255, 245, 235, 255)
C_SKIN_BASE = (255, 222, 202, 255)
C_SKIN_SHADOW = (238, 172, 138, 255)
C_SKIN_DEEP = (205, 122, 92, 255)

# Hair (Fiery Flame Emperor Spikes)
C_HAIR_HIGHLIGHT = (255, 215, 65, 255)
C_HAIR_ORANGE = (255, 115, 26, 255)
C_HAIR_RED = (228, 34, 24, 255)
C_HAIR_CRIMSON = (145, 15, 28, 255)
C_HAIR_DARK = (68, 5, 16, 255)

# Eyes
C_EYE_WHITE = (244, 246, 255, 255)
C_EYE_AMBER = (255, 195, 25, 255)
C_EYE_GOLD_GLOW = (255, 235, 90, 255)
C_EYE_PUPIL = (185, 20, 25, 255)
C_EYE_SHADOW = (180, 190, 205, 255)

# Clothes (Black Hunter Mantle & Coat with Gold / Crimson Trims)
C_COAT_BASE = (26, 26, 34, 255)
C_COAT_LIGHT = (48, 50, 65, 255)
C_COAT_SHADOW = (14, 14, 20, 255)
C_COAT_DEEP = (8, 8, 12, 255)

C_CRIMSON_TRIM = (212, 28, 38, 255)
C_CRIMSON_SHADOW = (128, 12, 22, 255)

C_GOLD_BASE = (255, 200, 50, 255)
C_GOLD_LIGHT = (255, 235, 120, 255)
C_GOLD_SHADOW = (168, 120, 22, 255)

C_SHIRT_DARK = (38, 38, 48, 255)
C_SHIRT_SHADOW = (22, 22, 30, 255)
C_BELT_LEATHER = (40, 24, 20, 255)


class PixelCanvas:
    """Helper for 100x125 retro pixel-grid operations."""

    def __init__(self):
        self.img = Image.new("RGBA", (GRID_W, GRID_H), C_TRANSPARENT)
        self.draw = ImageDraw.Draw(self.img)

    def p(self, x: int, y: int, color: Tuple[int, int, int, int]):
        """Set a single pixel."""
        if 0 <= x < GRID_W and 0 <= y < GRID_H:
            self.img.putpixel((x, y), color)

    def rect(self, x: int, y: int, w: int, h: int, color: Tuple[int, int, int, int]):
        """Fill a rectangle of pixels."""
        for px in range(x, x + w):
            for py in range(y, y + h):
                self.p(px, py, color)

    def hline(self, x: int, y: int, length: int, color: Tuple[int, int, int, int]):
        for px in range(x, x + length):
            self.p(px, y, color)

    def vline(self, x: int, y: int, length: int, color: Tuple[int, int, int, int]):
        for py in range(y, y + length):
            self.p(x, py, color)

    def poly(self, pts: List[Tuple[int, int]], color: Tuple[int, int, int, int]):
        self.draw.polygon(pts, fill=color)

    def to_rgba_400x500(self) -> Image.Image:
        """Upscale via NEAREST neighbor to preserve 100% sharp pixel blocks."""
        return self.img.resize(TARGET_SIZE, Image.Resampling.NEAREST)


def build_head() -> Image.Image:
    """Generate Flame Emperor's pixel art head & spiky flaming hair."""
    c = PixelCanvas()

    # --- 1. Face Silhouette & Base Skin ---
    # Chin & jaw at x: 42..57, y: 32..47
    face_pts = [
        (42, 32), (57, 32),
        (58, 37), (56, 43),
        (50, 48),  # Chin point
        (43, 43), (41, 37),
    ]
    c.poly(face_pts, C_SKIN_BASE)

    # Face shading (cheek & neck shadow)
    c.rect(44, 43, 12, 4, C_SKIN_SHADOW)
    c.p(49, 47, C_SKIN_DEEP)
    c.p(50, 47, C_SKIN_DEEP)
    c.hline(46, 45, 8, C_SKIN_SHADOW)

    # Face contour outline
    c.vline(41, 35, 4, C_BLACK_OUTLINE)
    c.vline(58, 35, 4, C_BLACK_OUTLINE)
    c.p(42, 39, C_BLACK_OUTLINE)
    c.p(57, 39, C_BLACK_OUTLINE)
    c.p(43, 41, C_BLACK_OUTLINE)
    c.p(56, 41, C_BLACK_OUTLINE)
    c.p(44, 43, C_BLACK_OUTLINE)
    c.p(55, 43, C_BLACK_OUTLINE)
    c.p(46, 45, C_BLACK_OUTLINE)
    c.p(53, 45, C_BLACK_OUTLINE)
    c.p(48, 47, C_BLACK_OUTLINE)
    c.p(51, 47, C_BLACK_OUTLINE)
    c.p(49, 48, C_BLACK_OUTLINE)
    c.p(50, 48, C_BLACK_OUTLINE)

    # Ears (Left ear: 38..41, Right ear: 58..61)
    c.rect(38, 34, 3, 5, C_SKIN_SHADOW)
    c.p(39, 35, C_SKIN_BASE)
    c.vline(37, 34, 5, C_BLACK_OUTLINE)
    c.p(38, 33, C_BLACK_OUTLINE)
    c.p(38, 39, C_BLACK_OUTLINE)

    c.rect(59, 34, 3, 5, C_SKIN_SHADOW)
    c.p(60, 35, C_SKIN_BASE)
    c.vline(62, 34, 5, C_BLACK_OUTLINE)
    c.p(61, 33, C_BLACK_OUTLINE)
    c.p(61, 39, C_BLACK_OUTLINE)

    # --- 2. Fiery Flame Emperor Hair (Wild spiky crown rising upward) ---
    hair_spikes = [
        # Top-center high flame horn
        [(48, 24), (51, 24), (54, 12), (50, 8), (46, 14)],
        # Left rising flame horn
        [(40, 27), (47, 24), (43, 12), (37, 9), (36, 17)],
        # Far-left outward spike
        [(34, 31), (41, 28), (35, 20), (28, 18), (30, 26)],
        # Far-left cheek spike
        [(32, 37), (38, 34), (32, 28), (27, 27), (29, 34)],
        # Right rising flame horn
        [(53, 24), (60, 27), (63, 17), (62, 9), (56, 12)],
        # Far-right outward spike
        [(58, 28), (65, 31), (69, 26), (71, 18), (64, 20)],
        # Far-right cheek spike
        [(61, 34), (67, 37), (70, 34), (72, 27), (67, 28)],
        # Bangs framing forehead
        [(42, 25), (58, 25), (55, 34), (50, 31), (45, 34)],
    ]
    for pts in hair_spikes:
        c.poly(pts, C_HAIR_CRIMSON)

    # Layer brighter flame red & orange inside hair
    inner_flames = [
        # Center core
        [(49, 23), (51, 23), (52, 14), (50, 11), (48, 15)],
        # Left core
        [(42, 25), (46, 23), (43, 15), (39, 12), (38, 18)],
        # Right core
        [(54, 23), (58, 25), (61, 18), (60, 12), (57, 15)],
        # Left bang
        [(43, 26), (46, 26), (45, 32), (43, 30)],
        # Right bang
        [(53, 26), (56, 26), (56, 30), (54, 32)],
        # Center bang
        [(48, 26), (51, 26), (51, 30), (49, 31)],
    ]
    for pts in inner_flames:
        c.poly(pts, C_HAIR_RED)

    # Layer golden fire highlights on tips
    gold_tips = [
        (50, 9), (50, 10), (49, 11),
        (37, 10), (38, 11), (36, 12),
        (62, 10), (61, 11), (63, 12),
        (28, 19), (29, 20),
        (71, 19), (70, 20),
        (45, 32), (54, 32), (50, 30),
    ]
    for px, py in gold_tips:
        c.p(px, py, C_HAIR_HIGHLIGHT)

    # Hair outline & dark separation crevices
    hair_outlines = [
        # Center peak
        (50, 8), (49, 8), (48, 9), (47, 11), (46, 14),
        (51, 8), (52, 9), (53, 11), (54, 13),
        # Left spikes
        (37, 9), (36, 10), (35, 12), (34, 16), (28, 18), (27, 27),
        # Right spikes
        (62, 9), (63, 10), (64, 12), (65, 16), (71, 18), (72, 27),
    ]
    for px, py in hair_outlines:
        c.p(px, py, C_BLACK_OUTLINE)

    # Neck
    c.rect(47, 48, 6, 5, C_SKIN_SHADOW)
    c.rect(48, 48, 4, 4, C_SKIN_BASE)
    c.vline(46, 48, 5, C_BLACK_OUTLINE)
    c.vline(53, 48, 5, C_BLACK_OUTLINE)

    return c.to_rgba_400x500()


def build_body() -> Image.Image:
    """Generate Flame Emperor's black hunter mantle with popped high collar & flame trims."""
    c = PixelCanvas()

    # --- 1. High Popped Collar (Behind neck and jaw) ---
    # Collar points: (40, 46) up to (37, 41), right to (62, 41), down to (59, 46)
    c.poly([(38, 41), (43, 47), (44, 52), (38, 50)], C_CRIMSON_SHADOW)
    c.poly([(61, 41), (56, 47), (55, 52), (61, 50)], C_CRIMSON_SHADOW)
    c.poly([(37, 40), (41, 46), (39, 48), (35, 43)], C_CRIMSON_TRIM)
    c.poly([(62, 40), (58, 46), (60, 48), (64, 43)], C_CRIMSON_TRIM)

    # Collar outlines
    c.vline(36, 40, 4, C_BLACK_OUTLINE)
    c.vline(63, 40, 4, C_BLACK_OUTLINE)

    # --- 2. Torso Silhouette (Hunter Mantle & Trench Coat) ---
    torso_pts = [
        (36, 53), (63, 53),
        (66, 68), (62, 78),
        (57, 85), (42, 85),
        (37, 78), (33, 68),
    ]
    c.poly(torso_pts, C_COAT_BASE)

    # Inner chest vest / undershirt
    c.poly([(44, 53), (55, 53), (53, 68), (46, 68)], C_SHIRT_DARK)

    # Deep coat folds & shading
    c.vline(35, 60, 15, C_COAT_SHADOW)
    c.vline(64, 60, 15, C_COAT_SHADOW)
    c.rect(38, 70, 6, 12, C_COAT_SHADOW)
    c.rect(55, 70, 6, 12, C_COAT_SHADOW)

    # --- 3. Crimson Flame Lapels & Gold Accents ---
    # Left crimson lapel
    c.poly([(42, 53), (46, 53), (44, 72), (40, 68)], C_CRIMSON_TRIM)
    c.vline(45, 54, 16, C_CRIMSON_SHADOW)
    # Right crimson lapel
    c.poly([(57, 53), (53, 53), (55, 72), (59, 68)], C_CRIMSON_TRIM)
    c.vline(54, 54, 16, C_CRIMSON_SHADOW)

    # Gold Hunter Brooch / Clasp at Neck
    c.rect(48, 53, 4, 4, C_GOLD_BASE)
    c.p(49, 54, C_GOLD_LIGHT)
    c.rect(47, 53, 6, 1, C_GOLD_SHADOW)
    c.rect(47, 56, 6, 1, C_GOLD_SHADOW)

    # Gold buttons on coat
    for by in [61, 67, 73]:
        c.p(45, by, C_GOLD_BASE)
        c.p(54, by, C_GOLD_BASE)
        c.p(45, by - 1, C_GOLD_LIGHT)
        c.p(54, by - 1, C_GOLD_LIGHT)

    # --- 4. Waist Belt & Solid Pelvis / Crotch Bridge ---
    # Belt at y: 77..80
    c.rect(38, 77, 24, 4, C_BELT_LEATHER)
    # Gold buckle
    c.rect(47, 76, 6, 5, C_GOLD_BASE)
    c.rect(48, 77, 4, 3, C_GOLD_LIGHT)
    c.p(49, 78, C_BLACK_OUTLINE)
    c.p(50, 78, C_BLACK_OUTLINE)

    # Pelvis bridge (y: 81..88, x: 40..60)
    c.poly([(40, 81), (59, 81), (58, 88), (41, 88)], C_COAT_BASE)
    c.vline(49, 81, 7, C_COAT_SHADOW)
    c.vline(50, 81, 7, C_COAT_SHADOW)

    # Torso outlines
    c.vline(36, 54, 24, C_BLACK_OUTLINE)
    c.vline(63, 54, 24, C_BLACK_OUTLINE)
    c.hline(41, 88, 18, C_BLACK_OUTLINE)

    return c.to_rgba_400x500()


def build_arm(side: str) -> Image.Image:
    """Generate Flame Emperor's modular pixel art arm with coat sleeve & black glove.
    
    Rig anchors:
    - Left shoulder: (32, 54), hand: (27, 76)
    - Right shoulder: (68, 54), hand: (73, 76)
    """
    c = PixelCanvas()
    is_left = (side == "left")

    if is_left:
        # Shoulder pauldron & upper arm
        c.poly([(28, 51), (36, 51), (35, 64), (27, 64)], C_COAT_BASE)
        c.poly([(28, 51), (34, 51), (33, 55), (28, 55)], C_COAT_LIGHT)
        # Forearm
        c.poly([(27, 64), (34, 64), (32, 74), (25, 74)], C_COAT_BASE)
        # Crimson sleeve cuff with gold trim
        c.rect(25, 71, 8, 3, C_CRIMSON_TRIM)
        c.hline(25, 71, 8, C_GOLD_BASE)
        c.hline(25, 73, 8, C_CRIMSON_SHADOW)
        # Black hunter combat glove & hand at socket (27, 76)
        c.rect(25, 74, 6, 6, C_BLACK_OUTLINE)
        c.rect(26, 75, 4, 4, C_COAT_LIGHT)
        c.rect(27, 79, 3, 2, C_BLACK_OUTLINE)
        # Outlines
        c.vline(27, 52, 22, C_BLACK_OUTLINE)
        c.vline(35, 52, 22, C_BLACK_OUTLINE)
    else:
        # Shoulder pauldron & upper arm
        c.poly([(64, 51), (72, 51), (73, 64), (65, 64)], C_COAT_BASE)
        c.poly([(66, 51), (72, 51), (72, 55), (67, 55)], C_COAT_LIGHT)
        # Forearm
        c.poly([(66, 64), (73, 64), (75, 74), (68, 74)], C_COAT_BASE)
        # Crimson sleeve cuff with gold trim
        c.rect(67, 71, 8, 3, C_CRIMSON_TRIM)
        c.hline(67, 71, 8, C_GOLD_BASE)
        c.hline(67, 73, 8, C_CRIMSON_SHADOW)
        # Black hunter combat glove & hand at socket (73, 76)
        c.rect(69, 74, 6, 6, C_BLACK_OUTLINE)
        c.rect(70, 75, 4, 4, C_COAT_LIGHT)
        c.rect(70, 79, 3, 2, C_BLACK_OUTLINE)
        # Outlines
        c.vline(64, 52, 22, C_BLACK_OUTLINE)
        c.vline(73, 52, 22, C_BLACK_OUTLINE)

    return c.to_rgba_400x500()


def build_leg(side: str) -> Image.Image:
    """Generate Flame Emperor's modular legs with dark trousers and knee-high combat boots."""
    c = PixelCanvas()
    is_left = (side == "left")

    if is_left:
        # Left Leg: Hip (41, 79) to Foot (41, 120)
        c.poly([(41, 86), (48, 86), (47, 102), (40, 102)], C_COAT_BASE)
        c.vline(44, 87, 14, C_COAT_LIGHT)
        # Knee-high combat boot (y: 102..120)
        c.poly([(39, 102), (47, 102), (46, 118), (38, 118)], C_COAT_SHADOW)
        # Crimson boot strap & gold buckle
        c.hline(39, 107, 8, C_CRIMSON_TRIM)
        c.p(43, 107, C_GOLD_BASE)
        c.hline(38, 114, 8, C_CRIMSON_TRIM)
        c.p(42, 114, C_GOLD_BASE)
        # Boot sole & toe
        c.rect(36, 118, 11, 3, C_BLACK_OUTLINE)
        # Outlines
        c.vline(39, 87, 31, C_BLACK_OUTLINE)
        c.vline(48, 87, 31, C_BLACK_OUTLINE)
    else:
        # Right Leg: Hip (59, 79) to Foot (59, 120)
        c.poly([(52, 86), (59, 86), (60, 102), (53, 102)], C_COAT_BASE)
        c.vline(56, 87, 14, C_COAT_LIGHT)
        # Knee-high combat boot (y: 102..120)
        c.poly([(53, 102), (61, 102), (62, 118), (54, 118)], C_COAT_SHADOW)
        # Crimson boot strap & gold buckle
        c.hline(53, 107, 8, C_CRIMSON_TRIM)
        c.p(57, 107, C_GOLD_BASE)
        c.hline(54, 114, 8, C_CRIMSON_TRIM)
        c.p(58, 114, C_GOLD_BASE)
        # Boot sole & toe
        c.rect(53, 118, 11, 3, C_BLACK_OUTLINE)
        # Outlines
        c.vline(52, 87, 31, C_BLACK_OUTLINE)
        c.vline(60, 87, 31, C_BLACK_OUTLINE)

    return c.to_rgba_400x500()


# --- EYE EXPRESSIONS ---
# Base eye positions on 100x125 grid:
# Left eye: x: 44..48, y: 35..38
# Right eye: x: 52..56, y: 35..38

def build_eyes_open() -> Image.Image:
    """Intense golden-amber eyes with sharp fiery glow & confident angled brows."""
    c = PixelCanvas()
    # Left eye
    c.rect(44, 35, 5, 4, C_EYE_WHITE)
    c.rect(45, 35, 3, 4, C_EYE_AMBER)
    c.p(46, 36, C_EYE_GOLD_GLOW)
    c.p(46, 37, C_EYE_PUPIL)
    c.hline(43, 34, 6, C_BLACK_OUTLINE)  # Upper lash
    c.hline(44, 39, 4, C_BLACK_OUTLINE)  # Lower rim
    # Left eyebrow (sharp angle)
    c.hline(43, 32, 6, C_HAIR_DARK)
    c.p(48, 33, C_HAIR_DARK)

    # Right eye
    c.rect(51, 35, 5, 4, C_EYE_WHITE)
    c.rect(52, 35, 3, 4, C_EYE_AMBER)
    c.p(53, 36, C_EYE_GOLD_GLOW)
    c.p(53, 37, C_EYE_PUPIL)
    c.hline(51, 34, 6, C_BLACK_OUTLINE)  # Upper lash
    c.hline(52, 39, 4, C_BLACK_OUTLINE)  # Lower rim
    # Right eyebrow (sharp angle)
    c.hline(51, 32, 6, C_HAIR_DARK)
    c.p(51, 33, C_HAIR_DARK)

    return c.to_rgba_400x500()


def build_eyes_closed() -> Image.Image:
    """Smug / relaxed closed eyes (arrogant horizontal lashes)."""
    c = PixelCanvas()
    # Left closed lash with slight upward arrogant flick
    c.hline(43, 36, 6, C_BLACK_OUTLINE)
    c.p(42, 35, C_BLACK_OUTLINE)
    c.hline(43, 33, 6, C_HAIR_DARK)

    # Right closed lash
    c.hline(51, 36, 6, C_BLACK_OUTLINE)
    c.p(57, 35, C_BLACK_OUTLINE)
    c.hline(51, 33, 6, C_HAIR_DARK)

    return c.to_rgba_400x500()


def build_eyes_angry() -> Image.Image:
    """Narrowed, blazing fiery glare with furrowed brows & burning irises."""
    c = PixelCanvas()
    # Left narrowed eye
    c.rect(44, 36, 5, 3, C_EYE_WHITE)
    c.rect(45, 36, 3, 3, C_HAIR_RED)
    c.p(46, 37, C_EYE_GOLD_GLOW)
    c.hline(43, 35, 6, C_BLACK_OUTLINE)
    # Angled furrowed brow
    c.p(48, 34, C_HAIR_DARK)
    c.p(47, 33, C_HAIR_DARK)
    c.hline(43, 32, 4, C_HAIR_DARK)

    # Right narrowed eye
    c.rect(51, 36, 5, 3, C_EYE_WHITE)
    c.rect(52, 36, 3, 3, C_HAIR_RED)
    c.p(53, 37, C_EYE_GOLD_GLOW)
    c.hline(51, 35, 6, C_BLACK_OUTLINE)
    # Angled furrowed brow
    c.p(51, 34, C_HAIR_DARK)
    c.p(52, 33, C_HAIR_DARK)
    c.hline(53, 32, 4, C_HAIR_DARK)

    return c.to_rgba_400x500()


def build_eyes_shocked() -> Image.Image:
    """Wide dilated eyes with raised brows."""
    c = PixelCanvas()
    # Left wide eye
    c.rect(43, 34, 6, 5, C_EYE_WHITE)
    c.rect(45, 35, 2, 3, C_EYE_AMBER)
    c.p(45, 36, C_EYE_PUPIL)
    c.hline(43, 33, 6, C_BLACK_OUTLINE)
    c.hline(44, 39, 4, C_BLACK_OUTLINE)
    # Raised arched brow
    c.hline(43, 30, 5, C_HAIR_DARK)

    # Right wide eye
    c.rect(51, 34, 6, 5, C_EYE_WHITE)
    c.rect(53, 35, 2, 3, C_EYE_AMBER)
    c.p(53, 36, C_EYE_PUPIL)
    c.hline(51, 33, 6, C_BLACK_OUTLINE)
    c.hline(52, 39, 4, C_BLACK_OUTLINE)
    # Raised arched brow
    c.hline(52, 30, 5, C_HAIR_DARK)

    return c.to_rgba_400x500()


# --- MOUTH EXPRESSIONS ---
# Mouth coordinate center: x: 48..52, y: 43..45

def build_mouth_neutral() -> Image.Image:
    """Calm, razor-sharp composed mouth line."""
    c = PixelCanvas()
    c.hline(48, 44, 5, C_BLACK_OUTLINE)
    c.p(49, 45, C_SKIN_SHADOW)
    c.p(50, 45, C_SKIN_SHADOW)
    return c.to_rgba_400x500()


def build_mouth_smirk() -> Image.Image:
    """Signature arrogant Flame Emperor one-sided cocky smirk."""
    c = PixelCanvas()
    c.p(47, 45, C_BLACK_OUTLINE)
    c.p(48, 44, C_BLACK_OUTLINE)
    c.p(49, 44, C_BLACK_OUTLINE)
    c.p(50, 43, C_BLACK_OUTLINE)
    c.p(51, 42, C_BLACK_OUTLINE)
    c.p(52, 42, C_BLACK_OUTLINE)
    # White flash of teeth in smirk
    c.p(50, 44, C_EYE_WHITE)
    c.p(51, 43, C_EYE_WHITE)
    return c.to_rgba_400x500()


def build_mouth_happy() -> Image.Image:
    """Confident grinning smile."""
    c = PixelCanvas()
    c.hline(47, 43, 7, C_BLACK_OUTLINE)
    c.rect(48, 44, 5, 2, C_EYE_WHITE)
    c.hline(48, 46, 5, C_BLACK_OUTLINE)
    return c.to_rgba_400x500()


def build_mouth_angry() -> Image.Image:
    """Open shouting mouth / battle roar with sharp teeth."""
    c = PixelCanvas()
    c.poly([(47, 43), (53, 43), (52, 47), (48, 47)], C_HAIR_DARK)
    c.hline(48, 43, 5, C_EYE_WHITE)  # Upper teeth
    c.hline(48, 46, 5, C_EYE_WHITE)  # Lower teeth
    c.hline(47, 42, 7, C_BLACK_OUTLINE)
    c.hline(48, 47, 5, C_BLACK_OUTLINE)
    c.vline(46, 43, 4, C_BLACK_OUTLINE)
    c.vline(54, 43, 4, C_BLACK_OUTLINE)
    return c.to_rgba_400x500()


def build_mouth_shocked() -> Image.Image:
    """Small open gasping 'O' mouth."""
    c = PixelCanvas()
    c.rect(48, 43, 4, 4, C_BLACK_OUTLINE)
    c.rect(49, 44, 2, 2, C_HAIR_DARK)
    return c.to_rgba_400x500()


def build_mouth_sad() -> Image.Image:
    """Condescending sneer / scowl."""
    c = PixelCanvas()
    c.p(47, 45, C_BLACK_OUTLINE)
    c.p(48, 44, C_BLACK_OUTLINE)
    c.p(49, 44, C_BLACK_OUTLINE)
    c.p(50, 44, C_BLACK_OUTLINE)
    c.p(51, 44, C_BLACK_OUTLINE)
    c.p(52, 45, C_BLACK_OUTLINE)
    return c.to_rgba_400x500()


def build_mouth_surprised() -> Image.Image:
    """Parted lips."""
    c = PixelCanvas()
    c.rect(48, 44, 4, 2, C_BLACK_OUTLINE)
    c.p(49, 44, C_EYE_WHITE)
    c.p(50, 44, C_EYE_WHITE)
    return c.to_rgba_400x500()


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Generating Flame Emperor 16-bit Pixel Art Rig in {OUT_DIR}...")

    layers: Dict[str, Image.Image] = {
        "head.png": build_head(),
        "body.png": build_body(),
        "left_arm.png": build_arm("left"),
        "right_arm.png": build_arm("right"),
        "left_leg.png": build_leg("left"),
        "right_leg.png": build_leg("right"),
        # Eyes
        "eyes_open.png": build_eyes_open(),
        "eyes_closed.png": build_eyes_closed(),
        "eyes_angry.png": build_eyes_angry(),
        "eyes_shocked.png": build_eyes_shocked(),
        # Mouths
        "mouth_neutral.png": build_mouth_neutral(),
        "mouth_smirk.png": build_mouth_smirk(),
        "mouth_happy.png": build_mouth_happy(),
        "mouth_angry.png": build_mouth_angry(),
        "mouth_shocked.png": build_mouth_shocked(),
        "mouth_sad.png": build_mouth_sad(),
        "mouth_surprised.png": build_mouth_surprised(),
    }

    for fname, img in layers.items():
        out_path = OUT_DIR / fname
        img.save(out_path, format="PNG")
        print(f"  ✓ Saved {fname} ({img.size[0]}x{img.size[1]})")

    print(f"Done! Successfully generated {len(layers)} pixel art layers for Flame Emperor.")


if __name__ == "__main__":
    main()
