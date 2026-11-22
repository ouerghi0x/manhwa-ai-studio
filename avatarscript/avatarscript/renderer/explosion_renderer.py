"""Procedural fiery explosion, blast shockwave, and floating embers renderer."""
import math
from dataclasses import dataclass
from typing import Optional, Tuple, Dict
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from avatarscript.runtime.interpolation import apply_easing


@dataclass
class ExplosionState:
    """Evaluated explosion effect state at timestamp t."""
    active: bool = False
    tau: float = 0.0               # Seconds since explosion start
    duration: float = 3.0          # Total duration
    scatter_duration: float = 0.5  # Phase 1: outward explosion burst
    hold_duration: float = 1.2     # Phase 2: zero-g hovering pieces & embers
    reassemble_duration: float = 1.3 # Phase 3: magnetic reassembly & reunion flare
    intensity: float = 1.0         # Blast power / particle dispersion multiplier
    fire: bool = True              # Enable procedural fire & ember effects
    color: str = "orange"          # Fire palette preset ("orange", "red", "blue", "purple", "gold")


def get_fire_palette(color_name: str) -> Dict[str, Tuple[int, int, int]]:
    """Return RGB palette colors for procedural fire and explosion blast."""
    c = str(color_name).lower().strip()
    if c in ("blue", "azure", "cyan"):
        return {
            "core": (255, 255, 255),
            "inner": (120, 230, 255),
            "mid": (20, 150, 255),
            "outer": (10, 40, 220),
            "spark": (200, 245, 255),
        }
    elif c in ("purple", "violet"):
        return {
            "core": (255, 240, 255),
            "inner": (240, 120, 255),
            "mid": (180, 40, 255),
            "outer": (90, 15, 180),
            "spark": (255, 200, 255),
        }
    elif c in ("red", "crimson"):
        return {
            "core": (255, 245, 180),
            "inner": (255, 120, 30),
            "mid": (230, 30, 20),
            "outer": (140, 10, 15),
            "spark": (255, 220, 150),
        }
    elif c in ("gold", "yellow"):
        return {
            "core": (255, 255, 255),
            "inner": (255, 240, 100),
            "mid": (255, 190, 20),
            "outer": (220, 120, 10),
            "spark": (255, 250, 200),
        }
    else:  # Default blazing flame orange
        return {
            "core": (255, 255, 240),
            "inner": (255, 215, 40),
            "mid": (255, 110, 15),
            "outer": (220, 30, 10),
            "spark": (255, 240, 160),
        }


class ExplosionRenderer:
    """Renders multi-layer procedural fireballs, shockwave rings, and drifting flame embers."""

    NUM_EMBERS = 54

    @classmethod
    def render_explosion(
        cls,
        state: ExplosionState,
        character_center: Tuple[float, float],
    ) -> Tuple[Optional[Tuple[Image.Image, int, int]], Optional[Tuple[Image.Image, int, int]]]:
        """Render explosion fire layers.

        Returns:
            ((behind_img, paste_x, paste_y), (front_img, paste_x, paste_y))
            - behind_img: Fireball bloom, shockwave rings, and back fire clouds (behind character).
            - front_img: White-hot core blast, blazing embers, and reunion sparks (in front of character).
        """
        if not state.active or not state.fire or state.intensity <= 0.01:
            return None, None

        tau = state.tau
        dur = max(0.1, state.duration)
        if tau < 0.0 or tau >= dur:
            return None, None

        s_dur = max(0.1, state.scatter_duration)
        h_dur = max(0.0, state.hold_duration)
        r_dur = max(0.1, state.reassemble_duration)

        tot = s_dur + h_dur + r_dur
        if abs(tot - dur) > 1e-4:
            f = dur / tot
            s_dur *= f
            h_dur *= f
            r_dur *= f

        palette = get_fire_palette(state.color)
        cx, cy = character_center
        # Adjust detonation origin slightly up toward the torso/chest center
        det_y = cy - 40.0

        # Bounding canvas dimensions
        box_w, box_h = 900, 900
        origin_x = box_w / 2.0
        origin_y = box_h / 2.0
        paste_x = int(round(cx - origin_x))
        paste_y = int(round(det_y - origin_y))

        behind_canvas = Image.new("RGBA", (box_w, box_h), (0, 0, 0, 0))
        front_canvas = Image.new("RGBA", (box_w, box_h), (0, 0, 0, 0))
        b_draw = ImageDraw.Draw(behind_canvas)
        f_draw = ImageDraw.Draw(front_canvas)

        S = state.intensity

        # =========================================================================
        # PHASE 1: INITIAL OUTWARD DETONATION & BLAST FIREBALL (0 <= tau < s_dur)
        # =========================================================================
        if tau < s_dur:
            u = tau / s_dur
            k_exp = apply_easing(u, "ease_out")

            # 1. Outer Expanding Shockwave Ring
            ring_rad = (35.0 + 260.0 * k_exp) * S
            ring_alpha = max(0, min(255, int(220.0 * (1.0 - u * 0.95))))
            ring_width = max(2, int(14.0 * (1.0 - u * 0.7) * S))
            if ring_alpha > 5:
                r_col = palette["mid"] + (ring_alpha,)
                b_draw.ellipse(
                    [
                        (origin_x - ring_rad, origin_y - ring_rad),
                        (origin_x + ring_rad, origin_y + ring_rad),
                    ],
                    outline=r_col,
                    width=ring_width,
                )
                # Second inner golden shockwave
                inner_ring_rad = ring_rad * 0.68
                inner_alpha = max(0, min(255, int(ring_alpha * 0.75)))
                ir_col = palette["inner"] + (inner_alpha,)
                b_draw.ellipse(
                    [
                        (origin_x - inner_ring_rad, origin_y - inner_ring_rad),
                        (origin_x + inner_ring_rad, origin_y + inner_ring_rad),
                    ],
                    outline=ir_col,
                    width=max(2, ring_width - 3),
                )

            # 2. Main Expanding Flame Fireball Clouds (Behind & Front)
            flame_scale = math.sin(math.pi * min(1.0, u * 1.2)) * (1.0 - u * 0.35)
            core_rad = (30.0 + 130.0 * flame_scale) * S

            if core_rad > 5:
                # Radial flame lobes around the detonation center
                num_lobes = 10
                for i in range(num_lobes):
                    lobe_angle = (i / num_lobes) * math.pi * 2.0 + u * 1.5
                    lobe_dist = core_rad * 0.75
                    lx = origin_x + math.cos(lobe_angle) * lobe_dist
                    ly = origin_y + math.sin(lobe_angle) * lobe_dist - 15.0 * u * S  # Thermal rise
                    lobe_rad = core_rad * 0.55
                    l_alpha = max(0, min(255, int(200.0 * (1.0 - u * 0.5))))

                    # Draw outer red puff
                    b_draw.ellipse(
                        [(lx - lobe_rad, ly - lobe_rad), (lx + lobe_rad, ly + lobe_rad)],
                        fill=palette["outer"] + (int(l_alpha * 0.65),),
                    )
                    # Draw mid orange puff
                    b_draw.ellipse(
                        [(lx - lobe_rad * 0.75, ly - lobe_rad * 0.75), (lx + lobe_rad * 0.75, ly + lobe_rad * 0.75)],
                        fill=palette["mid"] + (int(l_alpha * 0.85),),
                    )
                    # Draw inner yellow puff
                    f_draw.ellipse(
                        [(lx - lobe_rad * 0.45, ly - lobe_rad * 0.45), (lx + lobe_rad * 0.45, ly + lobe_rad * 0.45)],
                        fill=palette["inner"] + (l_alpha,),
                    )

                # Incandescent White-Hot Core Flash (Foreground center)
                flash_rad = max(4.0, core_rad * 0.45 * (1.0 - u * 0.6))
                flash_alpha = max(0, min(255, int(255.0 * (1.0 - u * 0.8))))
                f_draw.ellipse(
                    [(origin_x - flash_rad, origin_y - flash_rad), (origin_x + flash_rad, origin_y + flash_rad)],
                    fill=palette["core"] + (flash_alpha,),
                )

        # =========================================================================
        # PHASE 2: FLOATING ZERO-G EMBERS & DRIFTING SPARKS (s_dur <= tau < s_dur + h_dur)
        # =========================================================================
        elif tau < s_dur + h_dur:
            t_float = tau - s_dur
            # Soft pulsating heat glow behind the character
            glow_rad = (60.0 + 12.0 * math.sin(t_float * 4.0)) * S
            g_alpha = int(90.0 + 25.0 * math.cos(t_float * 5.0))
            b_draw.ellipse(
                [(origin_x - glow_rad, origin_y - glow_rad), (origin_x + glow_rad, origin_y + glow_rad)],
                fill=palette["outer"] + (max(0, min(255, int(g_alpha * 0.4))),),
            )
            b_draw.ellipse(
                [(origin_x - glow_rad * 0.6, origin_y - glow_rad * 0.6), (origin_x + glow_rad * 0.6, origin_y + glow_rad * 0.6)],
                fill=palette["mid"] + (max(0, min(255, int(g_alpha * 0.6))),),
            )

        # =========================================================================
        # PHASE 3: MAGNETIC INWARD REASSEMBLY & REUNION FLARE (tau >= s_dur + h_dur)
        # =========================================================================
        else:
            t_re = tau - (s_dur + h_dur)
            v = min(1.0, max(0.0, t_re / r_dur))

            # Inward converging heat vortex
            vortex_rad = (120.0 * (1.0 - v) + 20.0) * S
            v_alpha = max(0, min(255, int(150.0 * (1.0 - v))))
            b_draw.ellipse(
                [(origin_x - vortex_rad, origin_y - vortex_rad), (origin_x + vortex_rad, origin_y + vortex_rad)],
                fill=palette["mid"] + (int(v_alpha * 0.5),),
            )

            # Golden reunion spark snap at completion (v >= 0.85)
            if v >= 0.82:
                snap_prog = (v - 0.82) / 0.18  # 0.0 -> 1.0
                snap_rad = (10.0 + 45.0 * math.sin(math.pi * snap_prog)) * S
                s_alpha = max(0, min(255, int(240.0 * math.sin(math.pi * snap_prog))))
                f_draw.ellipse(
                    [(origin_x - snap_rad, origin_y - snap_rad), (origin_x + snap_rad, origin_y + snap_rad)],
                    fill=palette["core"] + (s_alpha,),
                )
                # Radial lens flare spikes
                for spike_angle in (0.0, math.pi * 0.25, math.pi * 0.5, math.pi * 0.75):
                    sp_len = snap_rad * 2.2
                    dx = math.cos(spike_angle) * sp_len
                    dy = math.sin(spike_angle) * sp_len
                    f_draw.line(
                        [(origin_x - dx, origin_y - dy), (origin_x + dx, origin_y + dy)],
                        fill=palette["spark"] + (s_alpha,),
                        width=max(1, int(3 * S)),
                    )

        # =========================================================================
        # PROCEDURAL EMBERS & SPARKS (ACTIVE ACROSS ALL PHASES)
        # =========================================================================
        for i in range(cls.NUM_EMBERS):
            rng = np.random.RandomState(i * 1013 + 37)
            angle = rng.uniform(0, math.pi * 2.0)
            max_dist = rng.uniform(90.0, 270.0) * S
            base_size = rng.uniform(2.5, 5.5) * S
            rise_speed = rng.uniform(25.0, 75.0)

            px = origin_x
            py = origin_y
            alpha = 255
            size = base_size

            if tau < s_dur:
                # Phase 1: Shooting outward fast with blast
                u = tau / s_dur
                d = max_dist * apply_easing(u, "ease_out")
                px = origin_x + math.cos(angle) * d
                py = origin_y + math.sin(angle) * d - rise_speed * u * 0.4
                alpha = int(245.0 * (1.0 - u * 0.25))
            elif tau < s_dur + h_dur:
                # Phase 2: Zero-g hovering and floating upward
                t_float = tau - s_dur
                # Float drift with gentle sine wave oscillation
                drift_x = 14.0 * math.sin(2.8 * t_float + i)
                drift_y = -rise_speed * t_float * 0.6 + 6.0 * math.cos(2.2 * t_float + i)
                px = origin_x + math.cos(angle) * max_dist + drift_x
                py = origin_y + math.sin(angle) * max_dist + drift_y
                # Flickering brightness
                flicker = 0.75 + 0.25 * math.sin(8.0 * t_float + i * 2)
                alpha = int(210.0 * flicker)
                size = max(1.5, base_size * (1.0 - 0.25 * (t_float / max(0.1, h_dur))))
            else:
                # Phase 3: Inward magnetic convergence toward center
                t_float_total = h_dur
                end_x = origin_x + math.cos(angle) * max_dist + 14.0 * math.sin(2.8 * t_float_total + i)
                end_y = origin_y + math.sin(angle) * max_dist - rise_speed * t_float_total * 0.6
                t_re = tau - (s_dur + h_dur)
                v = min(1.0, max(0.0, t_re / r_dur))
                e_in = apply_easing(v, "ease_in_out")
                px = (1.0 - e_in) * end_x + e_in * origin_x
                py = (1.0 - e_in) * end_y + e_in * origin_y
                alpha = int(220.0 * (1.0 - v * 0.9))
                size = max(1.2, base_size * (1.0 - v * 0.6))

            if alpha > 10:
                # Color gradient: hot inner spark vs outer ember
                spark_color = palette["spark"] if (i % 3 == 0) else (
                    palette["inner"] if (i % 2 == 0) else palette["mid"]
                )
                col = spark_color + (max(0, min(255, alpha)),)
                f_draw.ellipse(
                    [(px - size, py - size), (px + size, py + size)],
                    fill=col,
                )

        # Soft glow blur on behind canvas for atmospheric fire bloom
        behind_glow = behind_canvas.filter(ImageFilter.GaussianBlur(radius=4))
        behind_canvas = Image.alpha_composite(behind_glow, behind_canvas)

        return (behind_canvas, paste_x, paste_y), (front_canvas, paste_x, paste_y)
