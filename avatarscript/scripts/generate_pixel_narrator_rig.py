"""Pure 16-Bit Pixel Art Character Rig Generator for the Streamer / Commentary Narrator.

Drawn completely from scratch on a retro pixel grid based on the user-provided
reference illustration:
- Messy spiky black anime hair with ambient studio neon purple rim highlights
- Striking sapphire-blue eyes with deep pupils and white catchlights
- Black zip-up oversized hoodie with white drawstrings, metallic zipper, and inner black tee
- 100% vector-free, authentic integer pixel art upscaled 4x with NEAREST neighbor:
  - head.png
  - body.png
  - left_arm.png, right_arm.png
  - left_leg.png, right_leg.png
  - eyes_open.png, eyes_closed.png, eyes_angry.png, eyes_shocked.png
  - mouth_neutral.png, mouth_happy.png, mouth_angry.png, mouth_shocked.png, mouth_smirk.png, mouth_surprised.png, mouth_sad.png
  - assets/props/streamer_mic.png
"""
from pathlib import Path
from typing import Dict, List, Tuple
from PIL import Image, ImageDraw

GRID_W = 100
GRID_H = 125
SCALE = 4
TARGET_SIZE = (400, 500)

OUT_DIR = Path(__file__).resolve().parent.parent / "assets" / "characters" / "pixel_narrator"
PROPS_DIR = Path(__file__).resolve().parent.parent / "assets" / "props"

# --- PALETTE (Extracted accurately from the illustration) ---
C_TRANSPARENT = (0, 0, 0, 0)
C_OUTLINE = (18, 14, 24, 255)
C_DARK_PURPLE = (36, 24, 52, 255)

# Skin
C_SKIN_HIGHLIGHT = (255, 244, 236, 255)
C_SKIN_BASE = (254, 218, 198, 255)
C_SKIN_SHADOW = (242, 172, 146, 255)
C_SKIN_DEEP_SHADOW = (212, 134, 114, 255)
C_SKIN_PURPLE_SHADOW = (180, 115, 125, 255)

# Hair (Spiky messy black/indigo hair with neon purple rim lighting)
C_HAIR_BASE = (26, 22, 34, 255)
C_HAIR_SHADOW = (14, 12, 20, 255)
C_HAIR_MID = (42, 36, 56, 255)
C_HAIR_HIGHLIGHT = (72, 58, 98, 255)
C_HAIR_NEON_PURPLE = (156, 98, 246, 255)  # Bright studio neon rim light
C_HAIR_NEON_LIGHT = (205, 168, 255, 255)   # Specular crown / rim glow

# Eyes (Deep sapphire blue)
C_EYE_WHITE = (242, 246, 255, 255)
C_EYE_BLUE_BASE = (42, 88, 226, 255)
C_EYE_BLUE_LIGHT = (78, 142, 255, 255)
C_EYE_BLUE_PUPIL = (18, 36, 110, 255)
C_EYE_GLOW = (140, 195, 255, 255)
C_EYE_LASH = (16, 12, 22, 255)

# Clothes (Black Hoodie, White Strings, Silver Zipper, Dark Tee)
C_HOODIE_BASE = (28, 26, 36, 255)
C_HOODIE_SHADOW = (16, 14, 22, 255)
C_HOODIE_LIGHT = (48, 45, 62, 255)
C_HOODIE_NEON_RIM = (130, 80, 220, 255)
C_ZIPPER = (170, 175, 195, 255)
C_ZIPPER_SHADOW = (95, 100, 118, 255)
C_STRING_WHITE = (235, 238, 248, 255)
C_STRING_SHADOW = (160, 165, 185, 255)
C_INNER_SHIRT = (18, 16, 22, 255)


class PixelCanvas:
    """Helper for drawing on a 100x125 retro pixel canvas and upscaling 4x to 400x500."""

    def __init__(self):
        self.img = Image.new("RGBA", (GRID_W, GRID_H), C_TRANSPARENT)
        self.draw = ImageDraw.Draw(self.img)

    def p(self, x: int, y: int, color: Tuple[int, int, int, int]):
        if 0 <= x < GRID_W and 0 <= y < GRID_H:
            self.img.putpixel((x, y), color)

    def rect(self, x: int, y: int, w: int, h: int, color: Tuple[int, int, int, int]):
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

    def to_400x500(self) -> Image.Image:
        """Upscale 4x with nearest-neighbor to retain 100% crisp retro pixel blocks."""
        return self.img.resize(TARGET_SIZE, Image.Resampling.NEAREST)


def build_head() -> Image.Image:
    """Generate the streamer's spiky black hair with neon purple highlights and face base."""
    c = PixelCanvas()

    # --- 1. Face Contour & Neck ---
    # Neck: x in [46, 54], y in [48, 55]
    c.rect(47, 48, 7, 7, C_SKIN_PURPLE_SHADOW)
    c.rect(48, 48, 5, 5, C_SKIN_SHADOW)
    c.vline(46, 48, 7, C_OUTLINE)
    c.vline(54, 48, 7, C_OUTLINE)

    # Chin & Jaw:
    face_pts = [
        (42, 33), (58, 33),
        (59, 39), (57, 44),
        (50, 48),  # Pointed anime chin
        (43, 44), (41, 39),
    ]
    c.poly(face_pts, C_SKIN_BASE)

    # Face shading (chin shadow & cheeks)
    c.poly([(44, 44), (56, 44), (50, 48)], C_SKIN_SHADOW)
    c.hline(46, 46, 9, C_SKIN_PURPLE_SHADOW)

    # Jawline outline
    c.vline(41, 36, 4, C_OUTLINE)
    c.vline(59, 36, 4, C_OUTLINE)
    c.p(42, 40, C_OUTLINE)
    c.p(58, 40, C_OUTLINE)
    c.p(43, 42, C_OUTLINE)
    c.p(57, 42, C_OUTLINE)
    c.p(45, 45, C_OUTLINE)
    c.p(55, 45, C_OUTLINE)
    c.p(48, 47, C_OUTLINE)
    c.p(52, 47, C_OUTLINE)
    c.p(49, 48, C_OUTLINE)
    c.p(50, 48, C_OUTLINE)

    # Ears:
    c.rect(38, 34, 3, 5, C_SKIN_SHADOW)
    c.p(39, 35, C_SKIN_BASE)
    c.vline(37, 34, 5, C_OUTLINE)
    c.rect(59, 34, 3, 5, C_SKIN_SHADOW)
    c.p(60, 35, C_SKIN_BASE)
    c.vline(62, 34, 5, C_OUTLINE)

    # --- 2. Messy Spiky Black Anime Hair ---
    # Silhouette layers rising upward and spreading out with layered spikes
    hair_masses = [
        # Large central mane
        [(36, 27), (64, 27), (68, 18), (62, 10), (52, 7), (44, 9), (34, 16)],
        # Crown left spikes
        [(38, 18), (47, 10), (43, 6), (37, 8), (32, 13)],
        # Far-left wild lock
        [(34, 24), (28, 20), (25, 23), (27, 28), (33, 31)],
        # Left sideburn tufts
        [(32, 30), (27, 34), (28, 38), (34, 39), (37, 36)],
        # Crown right spikes
        [(53, 10), (62, 16), (67, 11), (65, 7), (57, 6)],
        # Far-right wild lock
        [(65, 22), (72, 18), (75, 21), (73, 27), (67, 30)],
        # Right sideburn tufts
        [(67, 30), (73, 34), (72, 38), (66, 39), (63, 36)],
    ]
    for pts in hair_masses:
        c.poly(pts, C_HAIR_BASE)

    # Hair midtones & texture strands (indigo / dark purple)
    mid_strands = [
        [(40, 24), (49, 14), (47, 10), (41, 14)],
        [(51, 14), (60, 24), (59, 17), (53, 10)],
        [(44, 8), (50, 7), (49, 12), (43, 12)],
        [(35, 18), (30, 23), (32, 26), (37, 21)],
        [(65, 18), (70, 23), (68, 26), (63, 21)],
    ]
    for pts in mid_strands:
        c.poly(pts, C_HAIR_MID)

    # Studio Neon Purple Rim Lighting (Iconic feature from the illustration!)
    # Glow on the left outer hair silhouette and crown tips
    neon_rim = [
        # Far-left rim
        (25, 23), (26, 22), (27, 21), (28, 20),
        (27, 34), (28, 33), (29, 32),
        # Crown left tips
        (37, 8), (38, 8), (43, 6), (44, 6),
        # Crown right tips
        (57, 6), (58, 6), (65, 7), (66, 7), (67, 11),
        # Far-right rim
        (72, 18), (73, 19), (74, 20), (75, 21),
    ]
    for px, py in neon_rim:
        c.p(px, py, C_HAIR_NEON_PURPLE)

    neon_highlights = [
        (43, 7), (57, 7), (28, 21), (73, 20),
    ]
    for px, py in neon_highlights:
        c.p(px, py, C_HAIR_NEON_LIGHT)

    # Outer black outline
    outer_spikes = [
        (43, 5), (44, 5), (57, 5), (58, 5),
        (36, 7), (37, 7), (65, 6), (66, 6),
        (24, 23), (25, 22), (75, 20), (76, 21),
        (26, 35), (27, 35), (73, 35), (74, 35),
    ]
    for px, py in outer_spikes:
        c.p(px, py, C_OUTLINE)

    # --- 3. Bangs Framing Forehead ---
    # Left bang cluster
    c.poly([(41, 26), (45, 26), (44, 35), (42, 33)], C_HAIR_BASE)
    c.vline(41, 26, 8, C_OUTLINE)
    c.p(44, 35, C_HAIR_HIGHLIGHT)

    # Center-left bang
    c.poly([(46, 25), (49, 25), (48, 33), (46, 32)], C_HAIR_BASE)
    c.p(48, 33, C_HAIR_MID)

    # Center-right long layered bang
    c.poly([(49, 25), (53, 25), (52, 36), (50, 35)], C_HAIR_BASE)
    c.vline(53, 25, 10, C_OUTLINE)
    c.p(52, 36, C_HAIR_HIGHLIGHT)

    # Right bang cluster
    c.poly([(54, 26), (58, 26), (58, 33), (55, 34)], C_HAIR_BASE)
    c.vline(58, 26, 8, C_OUTLINE)

    return c.to_400x500()


def build_body() -> Image.Image:
    """Generate the black zip-up hoodie with white drawstrings, metallic zipper, and inner tee."""
    c = PixelCanvas()

    # --- 1. Inner Crewneck Black Tee (visible at neck) ---
    c.poly([(45, 52), (55, 52), (53, 62), (47, 62)], C_INNER_SHIRT)
    c.hline(46, 53, 9, C_OUTLINE)

    # --- 2. Popped / Draped Hoodie Collar ---
    # Left hood flap
    c.poly([(36, 46), (44, 52), (45, 64), (35, 59)], C_HOODIE_BASE)
    c.poly([(36, 46), (42, 51), (40, 56), (35, 52)], C_HOODIE_LIGHT)
    # Right hood flap
    c.poly([(64, 46), (56, 52), (55, 64), (65, 59)], C_HOODIE_BASE)
    c.poly([(64, 46), (58, 51), (60, 56), (65, 52)], C_HOODIE_LIGHT)

    # Neon purple rim on left hood edge (studio ambient lighting)
    c.vline(35, 48, 10, C_HOODIE_NEON_RIM)
    c.vline(34, 52, 6, C_HOODIE_NEON_RIM)

    # --- 3. Oversized Hoodie Torso & Waistband ---
    torso_pts = [
        (33, 56), (67, 56),
        (71, 68), (65, 80),
        (62, 85), (38, 85),
        (35, 80), (29, 68),
    ]
    c.poly(torso_pts, C_HOODIE_BASE)

    # Hoodie shading & fabric folds
    c.rect(31, 66, 5, 14, C_HOODIE_SHADOW)
    c.rect(64, 66, 5, 14, C_HOODIE_SHADOW)
    c.rect(37, 74, 6, 10, C_HOODIE_SHADOW)
    c.rect(57, 74, 6, 10, C_HOODIE_SHADOW)

    # Center seam & Metallic Zipper (y in [58, 82])
    c.vline(49, 58, 25, C_ZIPPER_SHADOW)
    c.vline(50, 58, 25, C_ZIPPER)
    c.vline(51, 58, 25, C_ZIPPER_SHADOW)
    # Zipper pull tab at top
    c.rect(48, 58, 4, 3, C_ZIPPER)

    # --- 4. White Hoodie Drawstring Cords ---
    # Left string: dangles from (43, 58) down to (42, 75)
    c.vline(43, 58, 17, C_STRING_WHITE)
    c.vline(44, 58, 17, C_STRING_SHADOW)
    # Metal aglet tip
    c.rect(42, 73, 3, 3, C_ZIPPER)

    # Right string: dangles from (57, 58) down to (58, 73)
    c.vline(57, 58, 15, C_STRING_WHITE)
    c.vline(56, 58, 15, C_STRING_SHADOW)
    # Metal aglet tip
    c.rect(56, 71, 3, 3, C_ZIPPER)

    # --- 5. Ribbed Waistband Hem (y: 80..85) & Small Pelvis Crotch Junction (y: 85..89) ---
    c.rect(36, 81, 28, 4, C_HOODIE_LIGHT)
    c.hline(36, 85, 28, C_OUTLINE)

    # Pelvis bridge / crotch V-junction (ends at y: 89, leaves clean transparent gap below!)
    c.poly([(45, 85), (55, 85), (54, 88), (50, 89), (46, 88)], C_HOODIE_SHADOW)
    c.p(50, 89, C_OUTLINE)
    c.hline(46, 88, 9, C_OUTLINE)

    # Torso side outlines
    c.vline(33, 57, 24, C_OUTLINE)
    c.vline(67, 57, 24, C_OUTLINE)

    return c.to_400x500()


def build_arm(side: str) -> Image.Image:
    """Generate modular hoodie arm with cuff and skin hand."""
    c = PixelCanvas()
    is_left = (side == "left")

    if is_left:
        # Left shoulder at (32, 54), hand socket at (27, 76)
        c.poly([(28, 52), (36, 52), (35, 66), (26, 66)], C_HOODIE_BASE)
        c.vline(27, 53, 14, C_HOODIE_NEON_RIM)  # Neon purple highlight on left arm
        # Forearm
        c.poly([(26, 66), (34, 66), (31, 76), (24, 76)], C_HOODIE_BASE)
        # Ribbed Cuff
        c.rect(24, 73, 8, 3, C_HOODIE_SHADOW)
        # Hand
        c.rect(24, 76, 6, 6, C_SKIN_BASE)
        c.rect(25, 77, 4, 4, C_SKIN_HIGHLIGHT)
        c.rect(25, 80, 3, 2, C_SKIN_SHADOW)
        # Outline
        c.vline(26, 53, 24, C_OUTLINE)
        c.vline(34, 53, 24, C_OUTLINE)
    else:
        # Right shoulder at (68, 54), hand socket at (73, 76)
        c.poly([(64, 52), (72, 52), (74, 66), (65, 66)], C_HOODIE_BASE)
        # Forearm
        c.poly([(66, 66), (74, 66), (76, 76), (69, 76)], C_HOODIE_BASE)
        # Ribbed Cuff
        c.rect(68, 73, 8, 3, C_HOODIE_SHADOW)
        # Hand
        c.rect(70, 76, 6, 6, C_SKIN_BASE)
        c.rect(71, 77, 4, 4, C_SKIN_HIGHLIGHT)
        c.rect(71, 80, 3, 2, C_SKIN_SHADOW)
        # Outline
        c.vline(65, 53, 24, C_OUTLINE)
        c.vline(73, 53, 24, C_OUTLINE)

    return c.to_400x500()


def build_leg(side: str) -> Image.Image:
    """Generate clearly separated modular legs with dark trousers and streetwear sneakers.
    
    Ensures a clean, visible gap between the left and right thighs/calves/ankles
    so the legs are distinctly separated individual limbs.
    """
    c = PixelCanvas()
    is_left = (side == "left")

    C_PANTS_BASE = (22, 20, 30, 255)
    C_PANTS_LIGHT = (42, 38, 54, 255)
    C_PANTS_SHADOW = (14, 12, 18, 255)
    C_SNEAKER_BODY = (20, 18, 26, 255)
    C_SOLE_WHITE = (245, 246, 252, 255)
    C_SOLE_TREAD = (175, 180, 195, 255)

    if is_left:
        # Left Leg:
        # Thigh: x in [35, 45], y in [86, 103]
        c.poly([(36, 86), (45, 86), (44, 103), (35, 103)], C_PANTS_BASE)
        c.vline(38, 88, 14, C_PANTS_LIGHT)  # Thigh crease highlight
        c.vline(44, 88, 14, C_PANTS_SHADOW)  # Inseam shadow

        # Knee: y in [103, 106]
        c.hline(36, 103, 8, C_PANTS_LIGHT)

        # Lower Leg / Shin / Ankle: x in [35, 44], y in [106, 117]
        c.poly([(35, 106), (44, 106), (44, 117), (34, 117)], C_PANTS_BASE)
        c.vline(37, 107, 10, C_PANTS_LIGHT)

        # Streetwear Sneaker (y in [117, 124]):
        # Shoe upper
        c.poly([(32, 117), (44, 117), (45, 121), (31, 121)], C_SNEAKER_BODY)
        c.p(36, 118, C_SOLE_WHITE)  # Laces / accent
        c.p(39, 118, C_SOLE_WHITE)
        # White rubber sole (iconic sneaker profile)
        c.rect(30, 121, 16, 3, C_SOLE_WHITE)
        c.hline(30, 123, 16, C_SOLE_TREAD)

        # Clean outlines
        c.vline(35, 86, 31, C_OUTLINE)   # Outer seam
        c.vline(44, 88, 29, C_OUTLINE)   # Inner seam (defining the inseam gap!)
        c.hline(30, 124, 16, C_OUTLINE)  # Sole bottom outline
        c.vline(30, 121, 3, C_OUTLINE)
        c.vline(46, 121, 3, C_OUTLINE)
    else:
        # Right Leg:
        # Thigh: x in [55, 65], y in [86, 103]
        c.poly([(55, 86), (64, 86), (65, 103), (56, 103)], C_PANTS_BASE)
        c.vline(62, 88, 14, C_PANTS_LIGHT)  # Thigh crease highlight
        c.vline(56, 88, 14, C_PANTS_SHADOW)  # Inseam shadow

        # Knee: y in [103, 106]
        c.hline(56, 103, 8, C_PANTS_LIGHT)

        # Lower Leg / Shin / Ankle: x in [56, 65], y in [106, 117]
        c.poly([(56, 106), (65, 106), (66, 117), (56, 117)], C_PANTS_BASE)
        c.vline(63, 107, 10, C_PANTS_LIGHT)

        # Streetwear Sneaker (y in [117, 124]):
        # Shoe upper
        c.poly([(56, 117), (68, 117), (69, 121), (55, 121)], C_SNEAKER_BODY)
        c.p(61, 118, C_SOLE_WHITE)  # Laces / accent
        c.p(64, 118, C_SOLE_WHITE)
        # White rubber sole
        c.rect(54, 121, 16, 3, C_SOLE_WHITE)
        c.hline(54, 123, 16, C_SOLE_TREAD)

        # Clean outlines
        c.vline(56, 88, 29, C_OUTLINE)   # Inner seam (defining the inseam gap!)
        c.vline(65, 86, 31, C_OUTLINE)   # Outer seam
        c.hline(54, 124, 16, C_OUTLINE)  # Sole bottom outline
        c.vline(54, 121, 3, C_OUTLINE)
        c.vline(70, 121, 3, C_OUTLINE)

    return c.to_400x500()


# --- EYE EXPRESSIONS ---
# Base eye positions on 100x125 grid:
# Left eye:  x in [43, 48], y in [35, 39]
# Right eye: x in [52, 57], y in [35, 39]

def build_eyes_open() -> Image.Image:
    """Cool, focused sapphire-blue eyes with catchlight and dark defined lashes."""
    c = PixelCanvas()
    # Left Eye
    c.rect(43, 35, 5, 4, C_EYE_WHITE)
    c.rect(44, 35, 3, 4, C_EYE_BLUE_BASE)
    c.p(45, 36, C_EYE_BLUE_PUPIL)
    c.p(46, 36, C_EYE_GLOW)
    c.p(44, 35, (255, 255, 255, 255))  # White specular catchlight
    c.hline(42, 34, 6, C_EYE_LASH)     # Upper lash
    c.hline(43, 39, 4, C_OUTLINE)      # Lower lash
    # Eyebrow
    c.hline(42, 32, 6, C_HAIR_BASE)

    # Right Eye
    c.rect(52, 35, 5, 4, C_EYE_WHITE)
    c.rect(53, 35, 3, 4, C_EYE_BLUE_BASE)
    c.p(54, 36, C_EYE_BLUE_PUPIL)
    c.p(55, 36, C_EYE_GLOW)
    c.p(53, 35, (255, 255, 255, 255))  # White catchlight
    c.hline(52, 34, 6, C_EYE_LASH)     # Upper lash
    c.hline(53, 39, 4, C_OUTLINE)      # Lower lash
    # Eyebrow
    c.hline(52, 32, 6, C_HAIR_BASE)

    return c.to_400x500()


def build_eyes_closed() -> Image.Image:
    """Happy / relaxed anime closed crescent-moon eye slits."""
    c = PixelCanvas()
    # Left closed lash (upward curved arch)
    c.p(43, 36, C_EYE_LASH)
    c.p(44, 35, C_EYE_LASH)
    c.p(45, 35, C_EYE_LASH)
    c.p(46, 35, C_EYE_LASH)
    c.p(47, 36, C_EYE_LASH)
    c.hline(43, 32, 5, C_HAIR_BASE)

    # Right closed lash
    c.p(52, 36, C_EYE_LASH)
    c.p(53, 35, C_EYE_LASH)
    c.p(54, 35, C_EYE_LASH)
    c.p(55, 35, C_EYE_LASH)
    c.p(56, 36, C_EYE_LASH)
    c.hline(52, 32, 5, C_HAIR_BASE)

    return c.to_400x500()


def build_eyes_angry() -> Image.Image:
    """Narrowed furious blue glare with sharp angled furrowed brows."""
    c = PixelCanvas()
    # Left eye
    c.rect(43, 36, 5, 3, C_EYE_WHITE)
    c.rect(44, 36, 3, 3, C_EYE_BLUE_BASE)
    c.p(45, 37, C_EYE_BLUE_PUPIL)
    c.p(46, 37, C_EYE_GLOW)
    c.hline(42, 35, 6, C_EYE_LASH)
    # Angled furrowed brow
    c.p(47, 34, C_HAIR_BASE)
    c.p(46, 33, C_HAIR_BASE)
    c.hline(42, 32, 4, C_HAIR_BASE)

    # Right eye
    c.rect(52, 36, 5, 3, C_EYE_WHITE)
    c.rect(53, 36, 3, 3, C_EYE_BLUE_BASE)
    c.p(54, 37, C_EYE_BLUE_PUPIL)
    c.p(55, 37, C_EYE_GLOW)
    c.hline(52, 35, 6, C_EYE_LASH)
    # Angled furrowed brow
    c.p(52, 34, C_HAIR_BASE)
    c.p(53, 33, C_HAIR_BASE)
    c.hline(54, 32, 4, C_HAIR_BASE)

    # Pop-up angry vein icon in upper temple (💢 from illustration!)
    c.p(61, 30, (230, 40, 50, 255))
    c.p(63, 30, (230, 40, 50, 255))
    c.p(62, 31, (230, 40, 50, 255))
    c.p(61, 32, (230, 40, 50, 255))
    c.p(63, 32, (230, 40, 50, 255))

    return c.to_400x500()


def build_eyes_shocked() -> Image.Image:
    """Wide dilated pupils with raised brows and anime exclamation marks."""
    c = PixelCanvas()
    # Left wide eye
    c.rect(42, 34, 6, 5, C_EYE_WHITE)
    c.rect(44, 35, 2, 3, C_EYE_BLUE_BASE)
    c.p(44, 36, C_EYE_BLUE_PUPIL)
    c.hline(42, 33, 6, C_EYE_LASH)
    c.hline(42, 39, 6, C_OUTLINE)
    c.hline(42, 30, 5, C_HAIR_BASE)  # Raised brow

    # Right wide eye
    c.rect(52, 34, 6, 5, C_EYE_WHITE)
    c.rect(54, 35, 2, 3, C_EYE_BLUE_BASE)
    c.p(54, 36, C_EYE_BLUE_PUPIL)
    c.hline(52, 33, 6, C_EYE_LASH)
    c.hline(52, 39, 6, C_OUTLINE)
    c.hline(53, 30, 5, C_HAIR_BASE)  # Raised brow

    # Exclamation mark '!!' (from illustration top-middle!)
    c.rect(63, 26, 2, 5, (235, 45, 55, 255))
    c.p(63, 33, (235, 45, 55, 255))
    c.rect(67, 26, 2, 5, (235, 45, 55, 255))
    c.p(67, 33, (235, 45, 55, 255))

    return c.to_400x500()


# --- MOUTH EXPRESSIONS ---

def build_mouth_neutral() -> Image.Image:
    """Calm, sharp closed mouth line."""
    c = PixelCanvas()
    c.hline(48, 44, 5, C_OUTLINE)
    c.p(49, 45, C_SKIN_SHADOW)
    c.p(50, 45, C_SKIN_SHADOW)
    return c.to_400x500()


def build_mouth_happy() -> Image.Image:
    """Wide open cheerful laughing smile with teeth and pink tongue."""
    c = PixelCanvas()
    c.poly([(47, 43), (53, 43), (52, 47), (48, 47)], (180, 30, 50, 255))
    c.hline(48, 43, 5, (255, 255, 255, 255))  # Upper white teeth
    c.poly([(49, 45), (51, 45), (51, 47), (49, 47)], (255, 120, 140, 255))  # Pink tongue
    c.hline(47, 42, 7, C_OUTLINE)
    c.hline(48, 47, 5, C_OUTLINE)
    return c.to_400x500()


def build_mouth_angry() -> Image.Image:
    """Clenched / gritted teeth grimace."""
    c = PixelCanvas()
    c.rect(47, 43, 7, 3, (245, 245, 250, 255))  # White teeth
    c.hline(48, 44, 5, (180, 180, 190, 255))  # Center teeth division
    c.hline(47, 42, 7, C_OUTLINE)
    c.hline(47, 46, 7, C_OUTLINE)
    return c.to_400x500()


def build_mouth_shocked() -> Image.Image:
    """Open shouting 'O' mouth."""
    c = PixelCanvas()
    c.rect(48, 43, 4, 4, C_OUTLINE)
    c.rect(49, 44, 2, 2, (120, 20, 35, 255))
    return c.to_400x500()


def build_mouth_smirk() -> Image.Image:
    """Cocky one-sided smirk."""
    c = PixelCanvas()
    c.p(47, 45, C_OUTLINE)
    c.p(48, 44, C_OUTLINE)
    c.p(49, 44, C_OUTLINE)
    c.p(50, 43, C_OUTLINE)
    c.p(51, 43, C_OUTLINE)
    c.p(52, 42, C_OUTLINE)
    c.p(50, 44, (255, 255, 255, 255))
    return c.to_400x500()


def build_mouth_surprised() -> Image.Image:
    """Talking / open mouth flap."""
    c = PixelCanvas()
    c.rect(48, 43, 5, 3, C_OUTLINE)
    c.rect(49, 44, 3, 1, (220, 90, 110, 255))
    return c.to_400x500()


def build_mouth_sad() -> Image.Image:
    """Slight downturned frown / sighing mouth."""
    c = PixelCanvas()
    c.p(47, 45, C_OUTLINE)
    c.p(48, 44, C_OUTLINE)
    c.p(49, 44, C_OUTLINE)
    c.p(50, 44, C_OUTLINE)
    c.p(51, 45, C_OUTLINE)
    return c.to_400x500()


def build_streamer_mic() -> Image.Image:
    """Generate the studio broadcast condenser microphone on boom arm from illustration."""
    c = Image.new("RGBA", (140, 200), C_TRANSPARENT)
    draw = ImageDraw.Draw(c)

    # Metal boom arm swivel & stand
    draw.line([(70, 190), (70, 130)], fill=(45, 45, 58, 255), width=6)
    draw.line([(70, 130), (55, 110)], fill=(60, 60, 75, 255), width=6)

    # Shockmount ring
    draw.ellipse([30, 65, 110, 145], outline=(90, 90, 115, 255), width=4)
    draw.line([(40, 105), (100, 105)], fill=(120, 120, 150, 255), width=3)

    # Condenser Microphone Capsule (Cylindrical metal body with mesh grill)
    draw.rounded_rectangle([52, 40, 88, 120], radius=8, fill=(24, 24, 32, 255), outline=(15, 15, 20, 255), width=3)
    # Metallic grill (upper half)
    draw.rounded_rectangle([54, 42, 86, 75], radius=6, fill=(45, 48, 62, 255))
    for gy in range(45, 75, 4):
        draw.line([(55, gy), (85, gy)], fill=(110, 115, 140, 255), width=1)

    # Studio blue/cyan LED indicator
    draw.ellipse([67, 85, 73, 91], fill=(50, 220, 255, 255))
    return c


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    PROPS_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Generating Pure 16-Bit Pixel Art Rig for Pixel Narrator in {OUT_DIR}...")

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
        "mouth_happy.png": build_mouth_happy(),
        "mouth_angry.png": build_mouth_angry(),
        "mouth_shocked.png": build_mouth_shocked(),
        "mouth_smirk.png": build_mouth_smirk(),
        "mouth_surprised.png": build_mouth_surprised(),
        "mouth_sad.png": build_mouth_sad(),
    }

    for fname, img in layers.items():
        out_path = OUT_DIR / fname
        img.save(out_path, format="PNG")
        print(f"  ✓ Saved {fname} ({img.size[0]}x{img.size[1]})")

    # Prop
    mic_img = build_streamer_mic()
    mic_path = PROPS_DIR / "streamer_mic.png"
    mic_img.save(mic_path, format="PNG")
    print(f"  ✓ Saved studio prop: {mic_path.name} ({mic_img.size[0]}x{mic_img.size[1]})")

    # Also update streamer alias directory
    streamer_dir = OUT_DIR.parent / "streamer"
    streamer_dir.mkdir(parents=True, exist_ok=True)
    for fname, img in layers.items():
        img.save(streamer_dir / fname, format="PNG")

    print(f"\nDone! Successfully generated pure 16-bit pixel art character rig from scratch.")


if __name__ == "__main__":
    main()
