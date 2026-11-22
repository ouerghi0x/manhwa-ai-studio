"""Pixel Art Character Rig Generator for the Streamer / Commentary Narrator.

Extracts and synthesizes pixel-perfect 400x500 RGBA layers directly from the
user-uploaded illustration (media_1795130514245_1dfc63ce.jpg):
- head.png
- body.png
- left_arm.png
- right_arm.png
- left_leg.png
- right_leg.png
- eyes_open.png, eyes_closed.png, eyes_angry.png, eyes_shocked.png
- mouth_neutral.png, mouth_happy.png, mouth_angry.png, mouth_shocked.png, mouth_smirk.png, mouth_surprised.png, mouth_sad.png
- assets/props/streamer_mic.png
"""
from collections import deque
from pathlib import Path
from typing import Tuple
import numpy as np
from PIL import Image, ImageDraw

SRC_IMG = Path(r"C:/Users/wergh/.gemini/antigravity/brain/3e7fbc43-2da9-4def-8747-b8a63dd11861/.user_uploaded/media_1795130514245_1dfc63ce.jpg")
CHAR_DIR = Path(__file__).resolve().parent.parent / "assets" / "characters" / "pixel_narrator"
PROPS_DIR = Path(__file__).resolve().parent.parent / "assets" / "props"

RIG_SIZE = (400, 500)


def isolate_black_background(img_np: np.ndarray, thresh: Tuple[int, int, int] = (30, 26, 40)) -> np.ndarray:
    """Isolate subject by flood filling outer black background from borders."""
    h, w, _ = img_np.shape
    visited = np.zeros((h, w), dtype=bool)
    bg = np.zeros((h, w), dtype=bool)
    q = deque()

    def is_dark(y: int, x: int) -> bool:
        return (
            img_np[y, x, 0] <= thresh[0]
            and img_np[y, x, 1] <= thresh[1]
            and img_np[y, x, 2] <= thresh[2]
        )

    for x in range(w):
        if is_dark(0, x): q.append((0, x)); visited[0, x] = True
        if is_dark(h - 1, x): q.append((h - 1, x)); visited[h - 1, x] = True
    for y in range(h):
        if is_dark(y, 0): q.append((y, 0)); visited[y, 0] = True
        if is_dark(y, w - 1): q.append((y, w - 1)); visited[y, w - 1] = True

    while q:
        cy, cx = q.popleft()
        bg[cy, cx] = True
        for dy, dx in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            ny, nx = cy + dy, cx + dx
            if 0 <= ny < h and 0 <= nx < w and not visited[ny, nx]:
                if is_dark(ny, nx):
                    visited[ny, nx] = True
                    q.append((ny, nx))

    alpha = np.where(bg, 0, 255).astype(np.uint8)
    return np.dstack([img_np, alpha])


def build_rig_layer_canvas() -> Image.Image:
    """Create a transparent 400x500 RGBA canvas."""
    return Image.new("RGBA", RIG_SIZE, (0, 0, 0, 0))


def main():
    assert SRC_IMG.exists(), f"Source illustration not found at {SRC_IMG}"
    CHAR_DIR.mkdir(parents=True, exist_ok=True)
    PROPS_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Building Pixel Narrator / Streamer Character Rig from {SRC_IMG.name}...")

    src = Image.open(SRC_IMG)
    arr = np.array(src)

    # 1. Extract the 9 expression busts from right grid
    # Grid coordinates:
    cols = [(395, 600), (595, 800), (795, 1005)]
    rows = [(5, 192), (195, 384), (385, 574)]

    busts = {}
    bust_names = [
        ["neutral", "shocked", "angry"],
        ["think",   "happy",   "panic"],
        ["closed",  "point",   "bored"]
    ]

    for r_idx in range(3):
        for c_idx in range(3):
            name = bust_names[r_idx][c_idx]
            y0, y1 = rows[r_idx]
            x0, x1 = cols[c_idx]
            sub = arr[y0:y1, x0:x1].copy()
            rgba = isolate_black_background(sub)
            busts[name] = Image.fromarray(rgba)

    # Bust standard positioning on 400x500 rig canvas:
    # Scale 2x with NEAREST
    # Pasted at x = -5, y = -35 so head center = (200, 140..170) and shoulders = (130, 270)
    SCALE_FACTOR = 2
    PASTE_X = -5
    PASTE_Y = -35

    def scale_and_paste_bust(bust_img: Image.Image) -> Image.Image:
        b_2x = bust_img.resize(
            (bust_img.width * SCALE_FACTOR, bust_img.height * SCALE_FACTOR),
            Image.Resampling.NEAREST
        )
        canvas = build_rig_layer_canvas()
        canvas.paste(b_2x, (PASTE_X, PASTE_Y), b_2x)
        return canvas

    full_neutral = scale_and_paste_bust(busts["neutral"])
    full_shocked = scale_and_paste_bust(busts["shocked"])
    full_angry = scale_and_paste_bust(busts["angry"])
    full_happy = scale_and_paste_bust(busts["happy"])
    full_think = scale_and_paste_bust(busts["think"])
    full_closed = scale_and_paste_bust(busts["closed"])
    full_point = scale_and_paste_bust(busts["point"])
    full_bored = scale_and_paste_bust(busts["bored"])

    # --- 2. Separate Head Base, Body, Eyes & Mouth ---
    # Coordinates on the 400x500 rig canvas:
    # Eyes bounding box: y in [135, 185], x in [130, 275]
    # Mouth bounding box: y in [186, 230], x in [160, 240]
    # Head & hair: y <= 235
    # Body (hoodie collar & torso): y >= 200

    arr_neu = np.array(full_neutral)

    # A. Head Base Layer:
    # Contains hair, face shape, ears, chin, neck.
    # To allow expressions to overlay cleanly, we paint over the eye and mouth region with skin tone.
    head_arr = arr_neu.copy()
    # Mask out eyes and mouth: y in [135, 230], x in [135, 265]
    # In this region, replace facial feature pixels with base skin color
    SKIN_BASE = (248, 205, 178, 255)
    SKIN_SHADOW = (220, 160, 135, 255)

    for y in range(135, 230):
        for x in range(135, 265):
            if head_arr[y, x, 3] > 0:
                # If pixel is hair (dark), keep hair
                r, g, b, _ = head_arr[y, x]
                if r < 40 and g < 40 and b < 50:
                    continue  # Keep bangs / front hair
                # Otherwise, smooth skin base
                head_arr[y, x] = SKIN_SHADOW if y > 195 else SKIN_BASE

    head_img = Image.fromarray(head_arr)
    head_img.save(CHAR_DIR / "head.png")
    print("  ✓ Saved head.png")

    # B. Body Layer (Hoodie Torso & Shoulders):
    # Hoodie starts at neck (y: 200) down to y: 500
    body_arr = np.zeros((500, 400, 4), dtype=np.uint8)
    for y in range(195, 500):
        for x in range(400):
            if arr_neu[y, x, 3] > 0:
                body_arr[y, x] = arr_neu[y, x]

    # Solidify lower torso / hoodie base down to y: 500
    for y in range(330, 500):
        for x in range(50, 350):
            if body_arr[y, x, 3] == 0:
                # Black hoodie fabric
                body_arr[y, x] = (20, 20, 28, 255)
                if x in (198, 199, 201, 202):  # Zipper line
                    body_arr[y, x] = (80, 80, 100, 255)

    body_img = Image.fromarray(body_arr)
    body_img.save(CHAR_DIR / "body.png")
    print("  ✓ Saved body.png")

    # C. Extract Eye Expression Layers:
    # Bounding box: y in [130, 185], x in [130, 275]
    def extract_eyes(source_canvas: Image.Image) -> Image.Image:
        s_arr = np.array(source_canvas)
        out_arr = np.zeros((500, 400, 4), dtype=np.uint8)
        for y in range(130, 188):
            for x in range(130, 275):
                out_arr[y, x] = s_arr[y, x]
        return Image.fromarray(out_arr)

    eyes_open = extract_eyes(full_neutral)
    eyes_closed = extract_eyes(full_closed)
    eyes_angry = extract_eyes(full_angry)
    eyes_shocked = extract_eyes(full_shocked)

    eyes_open.save(CHAR_DIR / "eyes_open.png")
    eyes_closed.save(CHAR_DIR / "eyes_closed.png")
    eyes_angry.save(CHAR_DIR / "eyes_angry.png")
    eyes_shocked.save(CHAR_DIR / "eyes_shocked.png")
    print("  ✓ Saved eye expressions (open, closed, angry, shocked)")

    # D. Extract Mouth Expression Layers:
    # Bounding box: y in [188, 235], x in [155, 245]
    def extract_mouth(source_canvas: Image.Image) -> Image.Image:
        s_arr = np.array(source_canvas)
        out_arr = np.zeros((500, 400, 4), dtype=np.uint8)
        for y in range(188, 235):
            for x in range(155, 245):
                out_arr[y, x] = s_arr[y, x]
        return Image.fromarray(out_arr)

    mouth_neutral = extract_mouth(full_neutral)
    mouth_happy = extract_mouth(full_happy)
    mouth_angry = extract_mouth(full_angry)
    mouth_shocked = extract_mouth(full_shocked)
    mouth_smirk = extract_mouth(full_bored)
    mouth_surprised = extract_mouth(full_point)
    mouth_sad = extract_mouth(full_think)

    mouth_neutral.save(CHAR_DIR / "mouth_neutral.png")
    mouth_happy.save(CHAR_DIR / "mouth_happy.png")
    mouth_angry.save(CHAR_DIR / "mouth_angry.png")
    mouth_shocked.save(CHAR_DIR / "mouth_shocked.png")
    mouth_smirk.save(CHAR_DIR / "mouth_smirk.png")
    mouth_surprised.save(CHAR_DIR / "mouth_surprised.png")
    mouth_sad.save(CHAR_DIR / "mouth_sad.png")
    print("  ✓ Saved mouth expressions (neutral, happy, angry, shocked, smirk, surprised, sad)")

    # E. Modular Arms & Legs:
    # Shoulders at (130, 215) and (270, 215), hands at (110, 305) and (290, 305)
    def make_arm(side: str) -> Image.Image:
        c = build_rig_layer_canvas()
        draw = ImageDraw.Draw(c)
        is_left = (side == "left")
        sx, sy = (130, 215) if is_left else (270, 215)
        hx, hy = (110, 305) if is_left else (290, 305)

        # Draw hoodie sleeve segment
        arm_box = [min(sx, hx) - 18, sy - 10, max(sx, hx) + 18, hy + 5]
        draw.rounded_rectangle(arm_box, radius=12, fill=(22, 22, 30, 255), outline=(12, 12, 18, 255), width=3)
        # Sleeve cuff
        cuff_box = [hx - 14, hy - 8, hx + 14, hy + 6]
        draw.rounded_rectangle(cuff_box, radius=4, fill=(15, 15, 20, 255), outline=(10, 10, 14, 255), width=2)
        # Hand (fair skin)
        hand_box = [hx - 10, hy + 4, hx + 10, hy + 24]
        draw.rounded_rectangle(hand_box, radius=6, fill=SKIN_BASE, outline=(180, 130, 105, 255), width=2)
        return c

    left_arm = make_arm("left")
    right_arm = make_arm("right")
    left_arm.save(CHAR_DIR / "left_arm.png")
    right_arm.save(CHAR_DIR / "right_arm.png")
    print("  ✓ Saved left_arm.png and right_arm.png")

    # Legs:
    def make_leg(side: str) -> Image.Image:
        c = build_rig_layer_canvas()
        draw = ImageDraw.Draw(c)
        is_left = (side == "left")
        lx = 165 if is_left else 235
        # Dark trousers
        draw.rounded_rectangle([lx - 25, 340, lx + 25, 495], radius=6, fill=(16, 16, 22, 255), outline=(8, 8, 12, 255), width=3)
        return c

    left_leg = make_leg("left")
    right_leg = make_leg("right")
    left_leg.save(CHAR_DIR / "left_leg.png")
    right_leg.save(CHAR_DIR / "right_leg.png")
    print("  ✓ Saved left_leg.png and right_leg.png")

    # F. Studio Microphone Prop:
    # Extracted from the illustration (desktop broadcast condenser mic with boom arm)
    mic_raw = arr[255:455, 255:385].copy()
    # Mask out background
    mic_rgba = isolate_black_background(mic_raw, thresh=(45, 35, 60))
    mic_img = Image.fromarray(mic_rgba)
    mic_out = PROPS_DIR / "streamer_mic.png"
    mic_img.save(mic_out)
    print(f"  ✓ Saved studio prop: {mic_out.name}")

    print(f"\nDone! Successfully generated complete Pixel Narrator rig in {CHAR_DIR}")


if __name__ == "__main__":
    main()
