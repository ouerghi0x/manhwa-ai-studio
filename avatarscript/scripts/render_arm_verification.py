"""Generate high-res visual verification artifact for the new arm art and render video showcase."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from avatarscript.compiler.compiler import AvatarCompiler
from avatarscript.renderer.frame_renderer import FrameRenderer

ARTIFACT_DIR = Path("C:/Users/wergh/.gemini/antigravity/brain/27fab742-0fec-40a7-9ee2-b1108587c4b5")
JIN_DIR = Path("avatarscript/assets/characters/jin")
MED_DIR = Path("avatarscript/assets/characters/medazizwerghi")

# 1. Render an arm comparison board (Isolated Arm Assets + Hand Close-ups)
board = Image.new("RGBA", (1400, 750), (22, 24, 32, 255))
draw = ImageDraw.Draw(board)

# Load isolated arms
jin_l = Image.open(JIN_DIR / "left_arm.png").convert("RGBA")
jin_r = Image.open(JIN_DIR / "right_arm.png").convert("RGBA")
med_l = Image.open(MED_DIR / "left_arm.png").convert("RGBA")
med_r = Image.open(MED_DIR / "right_arm.png").convert("RGBA")

# Cards background
for x, title, subtitle in [
    (50, "Jin - Left Arm", "Black Hoodie, Ribbed Cuff & Manhwa Hand"),
    (380, "Jin - Right Arm", "Symmetrical Hoodie Sleeve & Relaxed Hand"),
    (720, "MedAziz - Left Arm", "Techwear Purple Sleeve & Bicep Cargo Pocket"),
    (1050, "MedAziz - Right Arm", "Yoke Seam, Ribbed Cuff & Anime Hand"),
]:
    draw.rounded_rectangle([x, 50, x + 300, 700], radius=16, fill=(30, 34, 46, 255), outline=(60, 68, 90, 255), width=2)
    draw.text((x + 20, 70), title, fill=(240, 244, 255, 255))
    draw.text((x + 20, 95), subtitle, fill=(150, 165, 195, 255))

# Paste arms centered in cards
board.paste(jin_l, (50, 140), jin_l)
board.paste(jin_r, (380, 140), jin_r)
board.paste(med_l, (720, 140), med_l)
board.paste(med_r, (1050, 140), med_r)

arm_board_path = ARTIFACT_DIR / "arm_art_verification.png"
board.save(arm_board_path)
print("Saved arm verification board to:", arm_board_path)

# 2. Render an assembled comparison of both characters
compiler = AvatarCompiler()
renderer = FrameRenderer()

script = """
scene "Arm Upgrade Verification":
    canvas 1920x1080
    fps 30
    duration 1.0s

    avatar "Jin":
        character "jin"
        position x:580 y:580
        scale 1.1

        at 0.0s:
            left_arm 25 duration 0.2s
            right_arm -15 duration 0.2s
            expression smirk

    avatar "MedAziz":
        character "medazizwerghi"
        position x:1340 y:580
        scale 1.1

        at 0.0s:
            left_arm -20 duration 0.2s
            right_arm 30 duration 0.2s
            expression happy
            hold item:"microphone" hand:right
"""
scene = compiler.compile_source(script)
assembled_frame = renderer.render_frame(scene.evaluate_at(0.5), transparent=False)
assembled_frame_path = ARTIFACT_DIR / "assembled_duo_new_arms.png"
assembled_frame.save(assembled_frame_path)
print("Saved assembled frame to:", assembled_frame_path)
