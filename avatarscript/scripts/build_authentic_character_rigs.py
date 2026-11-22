"""Extract and build authentic high-resolution modular character rigs for Jin and MedAziz.

Uses the authentic artwork from the user's uploaded sprite sheets and portraits:
- Character 1 (`jin`): Anime manhwa protagonist with glowing cyan eyes, black hoodie,
  charcoal tee, dark cargo jogger pants, and teal sneakers.
- Character 2 (`medazizwerghi`): Stylized anime creator with curly black fade hair,
  groomed beard, white AirPod in ear, purple techwear jacket, graphic tee, cargo pants,
  and purple sneakers.

Outputs 17 layers per character in 400x500 RGBA PNG format:
`body.png`, `head.png`, `left_arm.png`, `right_arm.png`, `left_leg.png`, `right_leg.png`,
4 eye expressions, and 7 mouth expressions.
"""
from __future__ import annotations

import math
from pathlib import Path
from typing import Dict, List, Tuple
from collections import deque
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

RIG_W, RIG_H = 400, 500

SCRATCH_DIR = Path(r"C:\Users\wergh\.gemini\antigravity\brain\27fab742-0fec-40a7-9ee2-b1108587c4b5\scratch")
CHAR_ROOT = Path(__file__).resolve().parent.parent / "assets" / "characters"
JIN_DIR = CHAR_ROOT / "jin"
MEDAZIZ_DIR = CHAR_ROOT / "medazizwerghi"


def clean_outer_white(im: Image.Image, threshold: int = 242) -> Image.Image:
    """Removes outer background white via border-connected BFS without erasing internal whites."""
    arr = np.array(im.convert("RGBA"))
    h, w, _ = arr.shape
    is_white = (arr[:, :, 0] >= threshold) & (arr[:, :, 1] >= threshold) & (arr[:, :, 2] >= threshold)

    visited = np.zeros((h, w), dtype=bool)
    q = deque()
    for x in range(w):
        if is_white[0, x]: visited[0, x] = True; q.append((0, x))
        if is_white[h - 1, x]: visited[h - 1, x] = True; q.append((h - 1, x))
    for y in range(h):
        if is_white[y, 0] and not visited[y, 0]: visited[y, 0] = True; q.append((y, 0))
        if is_white[y, w - 1] and not visited[y, w - 1]: visited[y, w - 1] = True; q.append((y, w - 1))

    while q:
        cy, cx = q.popleft()
        for dy, dx in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            ny, nx = cy + dy, cx + dx
            if 0 <= ny < h and 0 <= nx < w and not visited[ny, nx] and is_white[ny, nx]:
                visited[ny, nx] = True
                q.append((ny, nx))

    arr[visited, 3] = 0
    return Image.fromarray(arr)


def save_rgba(canvas: Image.Image, out_dir: Path, filename: str) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    canvas.save(out_dir / filename, format="PNG")


# ===========================================================================
# 1. BUILD JIN RIG (`jin`)
# ===========================================================================
def build_jin_rig() -> None:
    sheet1_path = Path(r"C:\Users\wergh\.gemini\antigravity\brain\27fab742-0fec-40a7-9ee2-b1108587c4b5\.user_uploaded\media_1794967288972_9f4d9a2e.jpg")
    s1 = clean_outer_white(Image.open(sheet1_path))

    # The authentic standing character in Sheet 1 is from (68, 204) to (334, 980)
    # Character dimension: width 266, height 776
    sc = 475.0 / 776.0
    cw = int(round(266 * sc))
    ch = int(round(776 * sc))

    # Scale the master standing sprite to 400x500 canvas
    master_char = s1.crop((68, 204, 334, 980)).resize((cw, ch), Image.Resampling.LANCZOS)
    ox = (RIG_W - cw) // 2
    oy = 15

    # Full character raster on 400x500 canvas:
    full_c = Image.new("RGBA", (RIG_W, RIG_H), (0, 0, 0, 0))
    full_c.paste(master_char, (ox, oy), master_char)

    arr = np.array(full_c)

    # 1. HEAD (Head, hair, ears, face base, neck down to chin ~y=108)
    head_mask = np.zeros((RIG_H, RIG_W), dtype=bool)
    head_mask[0:108, :] = True
    head_arr = np.copy(arr)
    head_arr[~head_mask] = 0
    head_img = Image.fromarray(head_arr)

    # Blank out eye sockets and mouth with matching skin tone (x: 180..220, y: 55..95)
    # Skin color in face center: (248, 222, 206, 255)
    skin_color = (248, 222, 206, 255)
    draw_h = ImageDraw.Draw(head_img)
    # Left eye socket blanking
    draw_h.ellipse([186, 60, 196, 68], fill=skin_color)
    # Right eye socket blanking
    draw_h.ellipse([206, 60, 216, 68], fill=skin_color)
    # Mouth blanking
    draw_h.ellipse([200, 80, 212, 85], fill=skin_color)
    save_rgba(head_img, JIN_DIR, "head.png")

    # 2. BODY (Hoodie torso, t-shirt, neck collar, kangaroo pocket, waist & belt down to hips y=265)
    # Extends up to y=88 so neck seamlessly tucks behind head.png
    body_mask = np.zeros((RIG_H, RIG_W), dtype=bool)
    body_mask[88:265, 140:260] = True
    body_arr = np.copy(arr)
    body_arr[~body_mask] = 0
    save_rgba(Image.fromarray(body_arr), JIN_DIR, "body.png")

    # 3. LEFT ARM (Left hoodie sleeve & hand, x: 100..152, y: 100..320)
    arm_l_mask = np.zeros((RIG_H, RIG_W), dtype=bool)
    arm_l_mask[100:320, 100:152] = True
    arm_l_arr = np.copy(arr)
    arm_l_arr[~arm_l_mask] = 0
    save_rgba(Image.fromarray(arm_l_arr), JIN_DIR, "left_arm.png")

    # 4. RIGHT ARM (Right hoodie sleeve & hand, x: 248..300, y: 100..320)
    arm_r_mask = np.zeros((RIG_H, RIG_W), dtype=bool)
    arm_r_mask[100:320, 248:300] = True
    arm_r_arr = np.copy(arr)
    arm_r_arr[~arm_r_mask] = 0
    save_rgba(Image.fromarray(arm_r_arr), JIN_DIR, "right_arm.png")

    # 5. LEFT LEG (Left cargo pant leg & teal sneaker, x: 125..202, y: 250..495)
    leg_l_mask = np.zeros((RIG_H, RIG_W), dtype=bool)
    leg_l_mask[250:495, 125:202] = True
    leg_l_arr = np.copy(arr)
    leg_l_arr[~leg_l_mask] = 0
    save_rgba(Image.fromarray(leg_l_arr), JIN_DIR, "left_leg.png")

    # 6. RIGHT LEG (Right cargo pant leg & teal sneaker, x: 198..275, y: 250..495)
    leg_r_mask = np.zeros((RIG_H, RIG_W), dtype=bool)
    leg_r_mask[250:495, 198:275] = True
    leg_r_arr = np.copy(arr)
    leg_r_arr[~leg_r_mask] = 0
    save_rgba(Image.fromarray(leg_r_arr), JIN_DIR, "right_leg.png")

    # --- EXPRESSIONS (Eyes & Mouths) ---
    # Eyes at x=191 and x=211, y=64. Mouth at x=206, y=82.
    # 1. eyes_open.png
    eyes_open_c = Image.new("RGBA", (RIG_W, RIG_H), (0, 0, 0, 0))
    d = ImageDraw.Draw(eyes_open_c)
    for cx in (191, 211):
        # Sclera
        d.ellipse([cx - 5.5, 61, cx + 5.5, 67], fill=(244, 248, 255, 255))
        # Glowing cyan iris
        d.ellipse([cx - 3.5, 61, cx + 3.5, 67], fill=(0, 210, 240, 255))
        d.ellipse([cx - 1.8, 62.5, cx + 1.8, 65.5], fill=(0, 130, 200, 255))
        d.ellipse([cx - 1, 62, cx + 0.5, 63.5], fill=(255, 255, 255, 255))
        # Upper lash line
        d.line([(cx - 6, 61), (cx + 6, 61)], fill=(14, 16, 24, 255), width=2)
        # Eyebrows
        d.line([(cx - 6, 56), (cx + 6, 55)], fill=(18, 20, 30, 255), width=2)
    save_rgba(eyes_open_c, JIN_DIR, "eyes_open.png")

    # 2. eyes_closed.png
    eyes_closed_c = Image.new("RGBA", (RIG_W, RIG_H), (0, 0, 0, 0))
    d = ImageDraw.Draw(eyes_closed_c)
    for cx in (191, 211):
        d.arc([cx - 5.5, 61, cx + 5.5, 67], start=0, end=180, fill=(18, 20, 30, 255), width=2)
        d.line([(cx - 6, 56), (cx + 6, 55)], fill=(18, 20, 30, 255), width=2)
    save_rgba(eyes_closed_c, JIN_DIR, "eyes_closed.png")

    # 3. eyes_angry.png
    eyes_angry_c = Image.new("RGBA", (RIG_W, RIG_H), (0, 0, 0, 0))
    d = ImageDraw.Draw(eyes_angry_c)
    for cx, sign in [(191, -1), (211, 1)]:
        d.ellipse([cx - 5, 62, cx + 5, 67], fill=(244, 248, 255, 255))
        d.ellipse([cx - 3, 62, cx + 3, 67], fill=(0, 220, 255, 255))
        d.ellipse([cx - 1.5, 63, cx + 1.5, 66], fill=(0, 140, 220, 255))
        d.line([(cx - 6, 62), (cx + 6, 62)], fill=(14, 16, 24, 255), width=2)
        # Slanted aggressive eyebrows
        d.line([(cx - sign * 6, 58), (cx + sign * 6, 54)], fill=(18, 20, 30, 255), width=2)
    save_rgba(eyes_angry_c, JIN_DIR, "eyes_angry.png")

    # 4. eyes_shocked.png
    eyes_shocked_c = Image.new("RGBA", (RIG_W, RIG_H), (0, 0, 0, 0))
    d = ImageDraw.Draw(eyes_shocked_c)
    for cx in (191, 211):
        d.ellipse([cx - 6, 59, cx + 6, 67], fill=(244, 248, 255, 255))
        d.ellipse([cx - 2.5, 62, cx + 2.5, 66], fill=(0, 210, 240, 255))
        d.ellipse([cx - 1, 63, cx + 1, 65], fill=(12, 14, 24, 255))
        d.arc([cx - 6, 59, cx + 6, 67], start=180, end=360, fill=(14, 16, 24, 255), width=2)
        d.line([(cx - 6, 53), (cx + 6, 53)], fill=(18, 20, 30, 255), width=2)
    save_rgba(eyes_shocked_c, JIN_DIR, "eyes_shocked.png")

    # Mouths:
    mouth_specs = {
        "mouth_neutral.png": lambda d: d.line([(201, 82), (211, 82)], fill=(48, 30, 26, 255), width=2),
        "mouth_smirk.png": lambda d: d.line([(201, 83), (212, 80)], fill=(48, 30, 26, 255), width=2),
        "mouth_sad.png": lambda d: d.arc([201, 81, 211, 88], start=180, end=360, fill=(48, 30, 26, 255), width=2),
        "mouth_happy.png": lambda d: (
            d.polygon([(201, 81), (211, 81), (209, 87), (203, 87)], fill=(120, 30, 40, 255)),
            d.polygon([(202, 81), (210, 81), (209, 83), (203, 83)], fill=(255, 255, 255, 255)),
            d.line([(201, 81), (211, 81)], fill=(48, 30, 26, 255), width=2),
        ),
        "mouth_angry.png": lambda d: (
            d.line([(201, 82), (211, 82)], fill=(48, 30, 26, 255), width=2),
            d.line([(203, 85), (209, 85)], fill=(190, 140, 120, 255), width=1),
        ),
        "mouth_surprised.png": lambda d: d.ellipse([203, 80, 209, 86], fill=(90, 25, 35, 255), outline=(48, 30, 26, 255), width=1),
        "mouth_shocked.png": lambda d: (
            d.ellipse([202, 79, 210, 88], fill=(80, 20, 30, 255), outline=(48, 30, 26, 255), width=1),
            d.line([(203, 81), (209, 81)], fill=(255, 255, 255, 255), width=1),
        ),
    }
    for mname, mdraw in mouth_specs.items():
        mc = Image.new("RGBA", (RIG_W, RIG_H), (0, 0, 0, 0))
        mdraw(ImageDraw.Draw(mc))
        save_rgba(mc, JIN_DIR, mname)


# ===========================================================================
# 2. BUILD MEDAZIZ RIG (`medazizwerghi`)
# ===========================================================================
def build_medaziz_rig() -> None:
    portrait_path = Path(r"C:\Users\wergh\.gemini\antigravity\brain\27fab742-0fec-40a7-9ee2-b1108587c4b5\.user_uploaded\media_1794967488027_2550bf00.jpg")
    s_med = clean_outer_white(Image.open(portrait_path))

    # In clean_medaziz_full.png, character bbox is (171, 43, 599, 1004)
    # Dimension: width 428, height 961
    sc = 475.0 / 961.0
    cw = int(round(428 * sc))
    ch = int(round(961 * sc))

    master_char = s_med.crop((171, 43, 599, 1004)).resize((cw, ch), Image.Resampling.LANCZOS)
    ox = (RIG_W - cw) // 2
    oy = 15

    # Full character raster on 400x500 canvas:
    full_c = Image.new("RGBA", (RIG_W, RIG_H), (0, 0, 0, 0))
    full_c.paste(master_char, (ox, oy), master_char)

    arr = np.array(full_c)

    # 1. HEAD (Head, curly fade hair, groomed beard, mustache, and AirPod down to collar y=106)
    head_mask = np.zeros((RIG_H, RIG_W), dtype=bool)
    head_mask[0:106, :] = True
    head_arr = np.copy(arr)
    head_arr[~head_mask] = 0
    head_img = Image.fromarray(head_arr)

    # Blank out eye sockets and mouth with matching skin tone
    skin_color = (235, 182, 148, 255)
    beard_color = (22, 18, 18, 255)
    draw_h = ImageDraw.Draw(head_img)
    # Eyes blanking
    draw_h.ellipse([181, 57, 191, 65], fill=skin_color)
    draw_h.ellipse([197, 57, 207, 65], fill=skin_color)
    # Mouth blanking & beard touch-up
    draw_h.ellipse([184, 72, 198, 80], fill=skin_color)
    draw_h.arc([183, 75, 199, 83], start=0, end=180, fill=beard_color, width=2)
    save_rgba(head_img, MEDAZIZ_DIR, "head.png")

    # 2. BODY (Purple tech jacket, black yoke, graphic tee, pockets, waist down to hips y=265)
    # Extends up to y=88 so neck seamlessly tucks behind head.png
    body_mask = np.zeros((RIG_H, RIG_W), dtype=bool)
    body_mask[88:265, 140:265] = True
    body_arr = np.copy(arr)
    body_arr[~body_mask] = 0
    save_rgba(Image.fromarray(body_arr), MEDAZIZ_DIR, "body.png")

    # 3. LEFT ARM (Left purple sleeve & hand near pocket, x: 100..155, y: 105..275)
    arm_l_mask = np.zeros((RIG_H, RIG_W), dtype=bool)
    arm_l_mask[105:275, 100:155] = True
    arm_l_arr = np.copy(arr)
    arm_l_arr[~arm_l_mask] = 0
    save_rgba(Image.fromarray(arm_l_arr), MEDAZIZ_DIR, "left_arm.png")

    # 4. RIGHT ARM (Right purple sleeve & gesturing hand, x: 255..335, y: 85..275)
    arm_r_mask = np.zeros((RIG_H, RIG_W), dtype=bool)
    arm_r_mask[85:275, 255:335] = True
    arm_r_arr = np.copy(arr)
    arm_r_arr[~arm_r_mask] = 0
    save_rgba(Image.fromarray(arm_r_arr), MEDAZIZ_DIR, "right_arm.png")

    # 5. LEFT LEG (Left cargo jogger & purple sneaker, x: 125..202, y: 250..495)
    leg_l_mask = np.zeros((RIG_H, RIG_W), dtype=bool)
    leg_l_mask[250:495, 125:202] = True
    leg_l_arr = np.copy(arr)
    leg_l_arr[~leg_l_mask] = 0
    save_rgba(Image.fromarray(leg_l_arr), MEDAZIZ_DIR, "left_leg.png")

    # 6. RIGHT LEG (Right cargo jogger & purple sneaker, x: 198..275, y: 250..495)
    leg_r_mask = np.zeros((RIG_H, RIG_W), dtype=bool)
    leg_r_mask[250:495, 198:275] = True
    leg_r_arr = np.copy(arr)
    leg_r_arr[~leg_r_mask] = 0
    save_rgba(Image.fromarray(leg_r_arr), MEDAZIZ_DIR, "right_leg.png")

    # --- EXPRESSIONS (Eyes & Mouths) ---
    # Eyes at x=186 and x=202, y=62. Mouth at x=191, y=76.
    # 1. eyes_open.png
    eyes_open_c = Image.new("RGBA", (RIG_W, RIG_H), (0, 0, 0, 0))
    d = ImageDraw.Draw(eyes_open_c)
    for cx in (186, 202):
        d.ellipse([cx - 5.5, 59, cx + 5.5, 65], fill=(248, 250, 255, 255))
        d.ellipse([cx - 3.5, 59, cx + 3.5, 65], fill=(96, 56, 34, 255))
        d.ellipse([cx - 1.8, 60.5, cx + 1.8, 63.5], fill=(20, 14, 14, 255))
        d.ellipse([cx - 1, 60, cx + 0.5, 61.5], fill=(255, 255, 255, 255))
        d.line([(cx - 6, 59), (cx + 6, 59)], fill=(20, 16, 18, 255), width=2)
        d.line([(cx - 6, 54), (cx + 6, 53)], fill=(22, 18, 18, 255), width=2)
    save_rgba(eyes_open_c, MEDAZIZ_DIR, "eyes_open.png")

    # 2. eyes_closed.png
    eyes_closed_c = Image.new("RGBA", (RIG_W, RIG_H), (0, 0, 0, 0))
    d = ImageDraw.Draw(eyes_closed_c)
    for cx in (186, 202):
        d.arc([cx - 5.5, 59, cx + 5.5, 65], start=0, end=180, fill=(22, 18, 18, 255), width=2)
        d.line([(cx - 6, 54), (cx + 6, 53)], fill=(22, 18, 18, 255), width=2)
    save_rgba(eyes_closed_c, MEDAZIZ_DIR, "eyes_closed.png")

    # 3. eyes_angry.png
    eyes_angry_c = Image.new("RGBA", (RIG_W, RIG_H), (0, 0, 0, 0))
    d = ImageDraw.Draw(eyes_angry_c)
    for cx, sign in [(186, -1), (202, 1)]:
        d.ellipse([cx - 5, 60, cx + 5, 65], fill=(248, 250, 255, 255))
        d.ellipse([cx - 3, 60, cx + 3, 65], fill=(96, 56, 34, 255))
        d.ellipse([cx - 1.5, 61, cx + 1.5, 64], fill=(20, 14, 14, 255))
        d.line([(cx - 6, 60), (cx + 6, 60)], fill=(20, 16, 18, 255), width=2)
        d.line([(cx - sign * 6, 56), (cx + sign * 6, 52)], fill=(22, 18, 18, 255), width=2)
    save_rgba(eyes_angry_c, MEDAZIZ_DIR, "eyes_angry.png")

    # 4. eyes_shocked.png
    eyes_shocked_c = Image.new("RGBA", (RIG_W, RIG_H), (0, 0, 0, 0))
    d = ImageDraw.Draw(eyes_shocked_c)
    for cx in (186, 202):
        d.ellipse([cx - 6, 57, cx + 6, 65], fill=(248, 250, 255, 255))
        d.ellipse([cx - 2.5, 60, cx + 2.5, 64], fill=(96, 56, 34, 255))
        d.ellipse([cx - 1, 61.5, cx + 1, 63.5], fill=(20, 14, 14, 255))
        d.arc([cx - 6, 57, cx + 6, 65], start=180, end=360, fill=(20, 16, 18, 255), width=2)
        d.line([(cx - 6, 51), (cx + 6, 51)], fill=(22, 18, 18, 255), width=2)
    save_rgba(eyes_shocked_c, MEDAZIZ_DIR, "eyes_shocked.png")

    # Mouths:
    mouth_specs = {
        "mouth_neutral.png": lambda d: d.line([(186, 76), (196, 76)], fill=(48, 30, 26, 255), width=2),
        "mouth_happy.png": lambda d: (
            d.polygon([(185, 75), (197, 75), (195, 81), (187, 81)], fill=(120, 30, 40, 255)),
            d.polygon([(186, 75), (196, 75), (195, 77), (187, 77)], fill=(255, 255, 255, 255)),
            d.line([(185, 75), (197, 75)], fill=(48, 30, 26, 255), width=2),
        ),
        "mouth_smirk.png": lambda d: d.line([(186, 77), (197, 74)], fill=(48, 30, 26, 255), width=2),
        "mouth_sad.png": lambda d: d.arc([186, 75, 196, 82], start=180, end=360, fill=(48, 30, 26, 255), width=2),
        "mouth_angry.png": lambda d: (
            d.line([(186, 76), (196, 76)], fill=(48, 30, 26, 255), width=2),
            d.line([(188, 79), (194, 79)], fill=(190, 140, 120, 255), width=1),
        ),
        "mouth_surprised.png": lambda d: d.ellipse([188, 74, 194, 79], fill=(90, 25, 35, 255), outline=(48, 30, 26, 255), width=1),
        "mouth_shocked.png": lambda d: (
            d.ellipse([187, 73, 195, 82], fill=(80, 20, 30, 255), outline=(48, 30, 26, 255), width=1),
            d.line([(188, 75), (194, 75)], fill=(255, 255, 255, 255), width=1),
        ),
    }
    for mname, mdraw in mouth_specs.items():
        mc = Image.new("RGBA", (RIG_W, RIG_H), (0, 0, 0, 0))
        mdraw(ImageDraw.Draw(mc))
        save_rgba(mc, MEDAZIZ_DIR, mname)


def main() -> None:
    print("Extracting authentic Jin (`jin`) rig...")
    build_jin_rig()
    print("Jin authentic rig complete: 17 layers generated.")

    print("Extracting authentic MedAziz (`medazizwerghi`) rig...")
    build_medaziz_rig()
    print("MedAziz authentic rig complete: 17 layers generated.")


if __name__ == "__main__":
    main()
