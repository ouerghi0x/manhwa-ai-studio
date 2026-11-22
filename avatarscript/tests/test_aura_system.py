"""Unit tests verifying the Dragon Ball Z-style Aura / Energy Highlighting System."""
import pytest
import numpy as np
from PIL import Image
from avatarscript.parser import AvatarParser
from avatarscript.compiler.compiler import AvatarCompiler
from avatarscript.renderer.aura_renderer import AuraRenderer, AuraState, hex_to_rgb
from avatarscript.renderer.frame_renderer import FrameRenderer


def test_aura_color_parsing():
    assert hex_to_rgb("gold") == (255, 215, 0)
    assert hex_to_rgb("blue") == (0, 190, 255)
    assert hex_to_rgb("red") == (255, 35, 45)
    assert hex_to_rgb("purple") == (180, 50, 255)
    assert hex_to_rgb("#ff0000") == (255, 0, 0)


def test_aura_non_destructive_character_preservation():
    """Verify that rendering an aura NEVER modifies the character sprite's original pixels or shape."""
    # Create a synthetic character sprite (e.g. 100x100 transparent image with a distinct shape)
    orig_char = Image.new("RGBA", (100, 100), (0, 0, 0, 0))
    # Draw a solid red square in the center
    for x in range(30, 70):
        for y in range(30, 70):
            orig_char.putpixel((x, y), (255, 50, 50, 255))

    char_copy = orig_char.copy()

    aura = AuraState(active=True, color="gold", intensity=1.5, size=25.0, speed=1.2, sparks=True)
    res = AuraRenderer.render_aura(orig_char, t=1.0, aura=aura)

    assert res is not None
    aura_img, off_x, off_y = res

    # 1. Original sprite is 100% byte-for-byte identical to char_copy
    assert list(orig_char.getdata()) == list(char_copy.getdata()), "Character pixels were modified!"

    # 2. Aura image is larger than the character sprite to encompass the outer flame bloom
    assert aura_img.width > orig_char.width
    assert aura_img.height > orig_char.height

    # 3. Compositing aura BEHIND character leaves original character pixels completely uncorrupted
    composite_canvas = Image.new("RGBA", (aura_img.width, aura_img.height), (0, 0, 0, 0))
    # Paste aura
    composite_canvas.alpha_composite(aura_img, (0, 0))
    # Paste character at -off_x, -off_y
    char_paste_pos = (-off_x, -off_y)
    composite_canvas.alpha_composite(orig_char, char_paste_pos)

    # Check that in the area where character is solid, pixel values match character exactly
    orig_arr = np.array(orig_char)
    comp_arr = np.array(composite_canvas)
    for y in range(30, 70):
        for x in range(30, 70):
            comp_px = comp_arr[char_paste_pos[1] + y, char_paste_pos[0] + x]
            orig_px = orig_arr[y, x]
            # Since character alpha is 255, composite result must match original character color
            assert np.array_equal(comp_px, orig_px), f"Mismatch at ({x}, {y}): {comp_px} vs {orig_px}"


def test_aura_compilation_and_timeline():
    """Verify parsing and timeline evaluation of aura statements."""
    code = """
scene "Aura Test":
    canvas 1920x1080
    fps 30
    duration 3.0s

    avatar "Goku":
        character "default"
        position center

        at 0.0s:
            expression neutral
            aura blue size:30 intensity:1.0 speed:1.0

        at 1.0s:
            aura gold size:50 intensity:2.0 speed:2.0 sparks:1 duration 0.5s

        at 2.0s:
            aura none duration 0.2s
"""
    compiler = AvatarCompiler()
    scene = compiler.compile_source(code)
    timeline = scene.avatars["Goku"]

    # At t=0.5s: Blue aura active
    state_0_5 = timeline.evaluate_at(0.5)
    assert state_0_5.aura.active is True
    assert state_0_5.aura.color == "blue"
    assert pytest.approx(state_0_5.aura.size, 0.1) == 30.0

    # At t=1.5s: Gold aura active, transitioned to higher intensity
    state_1_5 = timeline.evaluate_at(1.5)
    assert state_1_5.aura.active is True
    assert state_1_5.aura.color == "gold"
    assert pytest.approx(state_1_5.aura.size, 0.1) == 50.0
    assert pytest.approx(state_1_5.aura.intensity, 0.1) == 2.0

    # At t=2.5s: Aura deactivated
    state_2_5 = timeline.evaluate_at(2.5)
    assert state_2_5.aura.active is False
