"""Procedural animated Dragon Ball Z-style energy aura rendering system."""
import math
import numpy as np
from dataclasses import dataclass
from typing import Optional, Tuple
from PIL import Image, ImageFilter


def hex_to_rgb(hex_code: str) -> Tuple[int, int, int]:
    """Parse color name or hex into (R, G, B)."""
    c = hex_code.strip().lower()
    color_presets = {
        "gold": (255, 215, 0),
        "yellow": (255, 220, 20),
        "blue": (0, 190, 255),
        "cyan": (0, 240, 255),
        "red": (255, 35, 45),
        "purple": (180, 50, 255),
        "violet": (150, 30, 240),
        "green": (50, 255, 75),
        "white": (245, 248, 255),
        "orange": (255, 120, 20),
        "pink": (255, 90, 180),
    }
    if c in color_presets:
        return color_presets[c]
    if c.startswith("#"):
        h = c[1:]
        if len(h) == 3:
            h = "".join(ch * 2 for ch in h)
        if len(h) == 6:
            return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))
    return (255, 215, 0)


@dataclass
class AuraState:
    """Evaluated aura state at timestamp t."""
    active: bool = False
    color: str = "gold"
    intensity: float = 1.0  # Overall strength (0.0 to 2.0+)
    size: float = 35.0      # Aura flame bloom radius (pixels)
    speed: float = 1.0     # Animation cycle frequency multiplier
    sparks: bool = True     # Render electric sparks/lightning arcs


class AuraRenderer:
    """Renders a procedural, non-destructive DBZ energy aura layer behind a character sprite."""

    @staticmethod
    def render_aura(
        character_rgba: Image.Image,
        t: float,
        aura: AuraState,
    ) -> Optional[Tuple[Image.Image, int, int]]:
        """Generate an energy aura layer sized to match character_rgba.

        Returns (aura_rgba, offset_x, offset_y) to paste BEHIND character_rgba.
        The character_rgba is NEVER modified.
        """
        if not aura.active or aura.intensity <= 0.01:
            return None

        # Extract character alpha silhouette
        alpha_channel = character_rgba.split()[3]
        cw, ch = character_rgba.size
        if cw == 0 or ch == 0:
            return None

        # Padding for rising energy flames & outer electric sparks
        pad_x = int(max(40, aura.size * 1.5))
        pad_top = int(max(60, aura.size * 2.2))
        pad_bot = int(max(30, aura.size * 1.0))

        full_w = cw + pad_x * 2
        full_h = ch + pad_top + pad_bot

        # Base alpha canvas centered with padding
        base_alpha = Image.new("L", (full_w, full_h), 0)
        base_alpha.paste(alpha_channel, (pad_x, pad_top))

        # Time-based procedural phase parameters
        speed = max(0.1, aura.speed)
        pulse = 0.85 + 0.15 * math.sin(t * 12.0 * speed)
        flame_time = t * 14.0 * speed

        # --- STEP 1: INNER CORE GLOW (White-Hot Core) ---
        core_blur_rad = max(2, int(aura.size * 0.28 * pulse))
        core_alpha = base_alpha.filter(ImageFilter.GaussianBlur(radius=core_blur_rad))

        # --- STEP 2: RISING ENERGY FLAMES MASK (Procedural DBZ Plasma) ---
        alpha_np = np.array(base_alpha, dtype=np.float32) / 255.0

        # Downsample coordinates for procedural flame noise computation
        step = 4
        sub_h = full_h // step
        sub_w = full_w // step

        ys = np.arange(sub_h, dtype=np.float32)[:, None] * step
        xs = np.arange(sub_w, dtype=np.float32)[None, :] * step

        # Multi-octave upward streaming harmonic plasma waves
        wave1 = np.sin((xs * 0.045) + (ys * 0.035) + flame_time * 1.6)
        wave2 = np.cos((xs * 0.075) - (ys * 0.055) - flame_time * 2.4)
        wave3 = np.sin((xs * 0.12) + (ys * 0.09) + flame_time * 3.2)
        flame_noise = 0.5 + 0.25 * wave1 + 0.15 * wave2 + 0.10 * wave3

        # Resize flame noise to full resolution using PIL BICUBIC
        flame_img = Image.fromarray((flame_noise * 255.0).astype(np.uint8))
        flame_full = flame_img.resize((full_w, full_h), Image.Resampling.BICUBIC)
        flame_mask = np.array(flame_full, dtype=np.float32) / 255.0

        # --- STEP 3: PROCEDURAL SILHOUETTE EXPANSION & UPWARD FLAME STRETCH ---
        # Dilate silhouette upwards (energy flowing towards the sky)
        flame_shift = int(max(4, aura.size * 0.55 * pulse))
        flame_seed = Image.new("L", (full_w, full_h), 0)
        # Upward-biased offsets creating rising flame tongues
        flame_seed.paste(base_alpha, (0, -flame_shift))
        flame_seed = Image.blend(base_alpha, flame_seed, 0.45)

        # Outer energy bloom blur
        outer_blur_rad = max(4, int(aura.size * pulse))
        outer_alpha_img = flame_seed.filter(ImageFilter.GaussianBlur(radius=outer_blur_rad))
        outer_alpha_np = np.array(outer_alpha_img, dtype=np.float32) / 255.0

        # Ensure character silhouette is treated as a single unified container with zero joint gaps
        solid_char_img = base_alpha.filter(ImageFilter.MaxFilter(size=7)).filter(ImageFilter.MinFilter(size=7))
        char_mask_np = np.array(solid_char_img, dtype=np.float32) / 255.0

        # Modulate outer bloom with the animated rising plasma noise
        modulated_outer = outer_alpha_np * (0.45 + 0.75 * flame_mask)

        # Strictly outer halo: subtract the solid character container so glow never penetrates inside joints
        hollow_aura = np.maximum(0.0, modulated_outer - char_mask_np * 0.95)

        # --- STEP 4: COLOR COMPOSITING ---
        base_rgb = hex_to_rgb(aura.color)
        r_col, g_col, b_col = base_rgb

        # Hot tint for inner core (mixes base color with white-hot energy)
        core_r = min(255, int(r_col * 0.5 + 255 * 0.5))
        core_g = min(255, int(g_col * 0.5 + 255 * 0.5))
        core_b = min(255, int(b_col * 0.5 + 255 * 0.5))

        # RGBA canvas
        aura_canvas = Image.new("RGBA", (full_w, full_h), (0, 0, 0, 0))
        c_r = np.full((full_h, full_w), r_col, dtype=np.uint8)
        c_g = np.full((full_h, full_w), g_col, dtype=np.uint8)
        c_b = np.full((full_h, full_w), b_col, dtype=np.uint8)

        # Total alpha calculation - strictly an outer glow from the unified container
        core_np = np.array(core_alpha, dtype=np.float32) / 255.0
        outer_glow = np.maximum(0.0, core_np - char_mask_np * 0.95)
        total_alpha = np.clip(
            (hollow_aura * 1.5 + outer_glow * 0.8) * min(2.0, aura.intensity), 0.0, 1.0
        )
        c_a = (total_alpha * 240.0).astype(np.uint8)

        # Blend core hot tint where energy is most concentrated
        hot_mask = np.clip(core_np * 1.5, 0.0, 1.0)
        c_r = np.clip(c_r * (1.0 - hot_mask) + core_r * hot_mask, 0, 255).astype(np.uint8)
        c_g = np.clip(c_g * (1.0 - hot_mask) + core_g * hot_mask, 0, 255).astype(np.uint8)
        c_b = np.clip(c_b * (1.0 - hot_mask) + core_b * hot_mask, 0, 255).astype(np.uint8)

        aura_arr = np.dstack((c_r, c_g, c_b, c_a))
        aura_canvas = Image.fromarray(aura_arr)

        # --- STEP 5: ELECTRIC SPARKS & LIGHTNING ARCS (DBZ Super Saiyan 2 style) ---
        if aura.sparks:
            sparks_layer = Image.new("RGBA", (full_w, full_h), (0, 0, 0, 0))
            from PIL import ImageDraw
            sp_draw = ImageDraw.Draw(sparks_layer)

            # Seed pseudo-random sparks from quantized timestamp steps (60 Hz flicker)
            spark_time_bucket = int(t * 30.0 * speed)
            rng = np.random.RandomState(spark_time_bucket % 10000)

            # Spawn 3 to 7 jagged lightning bolts around the character silhouette
            num_bolts = rng.randint(3, 7)
            # Find silhouette boundary points
            boundary_y, boundary_x = np.where(
                (char_mask_np > 0.1) & (char_mask_np < 0.95)
            )

            if len(boundary_x) > 50:
                for _ in range(num_bolts):
                    idx = rng.randint(0, len(boundary_x))
                    sx, sy = boundary_x[idx], boundary_y[idx]

                    # Bolt radiates outward and upward
                    angle = rng.uniform(-math.pi * 0.85, -math.pi * 0.15)
                    bolt_len = rng.uniform(aura.size * 0.8, aura.size * 2.2)

                    # 3-segment jagged line
                    segments = 3
                    curr_x, curr_y = float(sx), float(sy)
                    pts = [(curr_x, curr_y)]
                    for s_i in range(segments):
                        frac = (s_i + 1) / segments
                        target_bx = sx + math.cos(angle) * bolt_len * frac
                        target_by = sy + math.sin(angle) * bolt_len * frac
                        # Add perpendicular displacement
                        perp_disp = rng.uniform(-14.0, 14.0)
                        curr_x = target_bx - math.sin(angle) * perp_disp
                        curr_y = target_by + math.cos(angle) * perp_disp
                        pts.append((curr_x, curr_y))

                    # Electric color: bright cyan/white or golden spark
                    spark_color = (255, 255, 255, 245) if rng.rand() > 0.4 else (core_r, core_g, 255, 230)
                    for p_i in range(len(pts) - 1):
                        sp_draw.line(
                            [pts[p_i], pts[p_i + 1]],
                            fill=spark_color,
                            width=rng.randint(2, 4),
                        )

            # Soft glow for sparks
            sparks_glow = sparks_layer.filter(ImageFilter.GaussianBlur(radius=2))
            aura_canvas.alpha_composite(sparks_glow)
            aura_canvas.alpha_composite(sparks_layer)

        # Return (aura_image, offset_x, offset_y) relative to the unpadded character sprite top-left
        return (aura_canvas, -pad_x, -pad_top)
