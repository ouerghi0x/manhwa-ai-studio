"""Frame renderer and pure-Python SVG/PNG layer rasterizer for AvatarScript."""
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, Optional, Tuple
from PIL import Image, ImageDraw
from avatarscript.runtime.scene import SceneState
from avatarscript.runtime.avatar import AvatarState, get_character_rig_config
from avatarscript.renderer.aura_renderer import AuraRenderer
from avatarscript.renderer.explosion_renderer import ExplosionRenderer


def parse_color(color_str: Optional[str]) -> Optional[Tuple[int, int, int, int]]:
    """Parse hex color (#RRGGBB or #RGB) to RGBA tuple."""
    if not color_str or color_str.lower() in ("none", "transparent"):
        return None
    c = color_str.strip()
    if c.startswith("#"):
        h = c[1:]
        if len(h) == 3:
            h = "".join(ch * 2 for ch in h)
        if len(h) == 6:
            return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), 255)
        if len(h) == 8:
            return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), int(h[6:8], 16))
    return (32, 32, 32, 255)


class SVGRasterizer:
    """Layer loader supporting 2x supersampled SVG vectors and RGBA PNG sprites."""

    RIG_SIZE: Tuple[int, int] = (400, 500)
    SUPPORTED_EXTENSIONS: Tuple[str, ...] = (".png", ".svg")
    OPTIONAL_LAYER_STEMS: Tuple[str, ...] = (
        "back_hair",
        "cape",
        "jacket_back",
        "coat_back",
        "pants",
        "bottoms",
        "footwear",
        "left_leg",
        "right_leg",
        "belt",
        "waist_accessory",
        "undershirt",
        "inner_top",
        "ear_accessory",
        "earrings",
        "front_hair",
        "hair",
        "jacket_sleeves",
        "jacket_sleeve_left",
        "jacket_sleeve_right",
        "jacket_front_flaps",
        "jacket_front",
    )

    def __init__(self, assets_root: Path):
        self.assets_root = assets_root
        self._cache: Dict[str, Image.Image] = {}

    def has_layer_asset(self, character: str, filename: str, is_prop: bool = False) -> bool:
        """Return True if a matching layer file (.png or .svg) exists for the character/prop."""
        try:
            self._resolve_asset_path(character, filename, is_prop=is_prop)
            return True
        except FileNotFoundError:
            return False

    def _find_by_stem(self, base_dir: Path, stem: str) -> Optional[Path]:
        """Find a matching asset file by stem across supported extensions."""
        for ext in self.SUPPORTED_EXTENSIONS:
            candidate = base_dir / f"{stem}{ext}"
            if candidate.exists():
                return candidate
        return None

    def _resolve_asset_path(self, character: str, filename: str, is_prop: bool = False) -> Path:
        """Resolve a character layer or prop path (.png preferred over default .svg), with fallbacks."""
        base_dir = self.assets_root / "props" if is_prop else self.assets_root / "characters" / character
        requested = base_dir / filename
        req_path = Path(filename)
        if req_path.suffix.lower() == ".png" and requested.exists():
            return requested

        stem = req_path.stem
        sibling = self._find_by_stem(base_dir, stem)
        if sibling is not None:
            return sibling

        if requested.exists():
            return requested

        if not is_prop:
            if stem.startswith("eyes_") and stem != "eyes_open":
                fallback = self._find_by_stem(base_dir, "eyes_open")
                if fallback is not None:
                    return fallback
            elif stem.startswith("mouth_") and stem != "mouth_neutral":
                fallback = self._find_by_stem(base_dir, "mouth_neutral")
                if fallback is not None:
                    return fallback

        raise FileNotFoundError(f"Missing layer asset (.svg/.png): {requested}")

    @staticmethod
    def load_png(
        png_path: Path,
        target_size: Optional[Tuple[int, int]] = None,
        is_pixel_art: bool = False,
    ) -> Image.Image:
        """Load a PNG as RGBA, optionally fitting it aspect-safely inside target_size."""
        with Image.open(png_path) as src:
            img = src.convert("RGBA")

        if target_size is None or img.size == target_size:
            return img

        tw, th = target_size
        scale = min(tw / img.width, th / img.height)
        nw = max(1, int(round(img.width * scale)))
        nh = max(1, int(round(img.height * scale)))
        resample_filter = Image.Resampling.NEAREST if is_pixel_art else Image.Resampling.LANCZOS
        resized = img.resize((nw, nh), resample_filter)

        canvas = Image.new("RGBA", target_size, (0, 0, 0, 0))
        ox = (tw - nw) // 2
        oy = (th - nh) // 2
        canvas.paste(resized, (ox, oy), resized)
        return canvas

    def load_layer_image(
        self,
        character: str,
        filename: str,
        is_prop: bool = False,
        is_pixel_art: bool = False,
    ) -> Image.Image:
        cache_key = f"prop/{filename}" if is_prop else f"{character}/{filename}:px={is_pixel_art}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        asset_path = self._resolve_asset_path(character, filename, is_prop=is_prop)
        if asset_path.suffix.lower() == ".png":
            target_size = None if is_prop else self.RIG_SIZE
            img = self.load_png(asset_path, target_size=target_size, is_pixel_art=is_pixel_art)
        else:
            img = self.rasterize_svg(asset_path)

        self._cache[cache_key] = img
        return img

    @staticmethod
    def rasterize_svg(svg_path: Path, supersample: int = 2) -> Image.Image:
        tree = ET.parse(svg_path)
        root = tree.getroot()
        view_box = root.attrib.get("viewBox", "0 0 400 500").split()
        vw, vh = int(float(view_box[2])), int(float(view_box[3]))

        ss = supersample
        canvas = Image.new("RGBA", (vw * ss, vh * ss), (0, 0, 0, 0))
        draw = ImageDraw.Draw(canvas)

        for elem in root:
            tag = elem.tag.split("}")[-1]
            fill = parse_color(elem.attrib.get("fill"))
            stroke = parse_color(elem.attrib.get("stroke"))
            sw = int(round(float(elem.attrib.get("stroke-width", "0")) * ss))

            if tag == "rect":
                x = float(elem.attrib.get("x", 0)) * ss
                y = float(elem.attrib.get("y", 0)) * ss
                w = float(elem.attrib.get("width", 0)) * ss
                h = float(elem.attrib.get("height", 0)) * ss
                rx = float(elem.attrib.get("rx", 0)) * ss
                if rx > 0:
                    draw.rounded_rectangle(
                        [x, y, x + w, y + h], radius=rx, fill=fill, outline=stroke, width=sw
                    )
                else:
                    draw.rectangle([x, y, x + w, y + h], fill=fill, outline=stroke, width=sw)

            elif tag == "circle":
                cx = float(elem.attrib.get("cx", 0)) * ss
                cy = float(elem.attrib.get("cy", 0)) * ss
                r = float(elem.attrib.get("r", 0)) * ss
                draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=fill, outline=stroke, width=sw)

            elif tag == "ellipse":
                cx = float(elem.attrib.get("cx", 0)) * ss
                cy = float(elem.attrib.get("cy", 0)) * ss
                rx = float(elem.attrib.get("rx", 0)) * ss
                ry = float(elem.attrib.get("ry", 0)) * ss
                draw.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], fill=fill, outline=stroke, width=sw)

            elif tag == "polygon":
                pts_raw = re.findall(r"[-+]?\d*\.?\d+", elem.attrib.get("points", ""))
                pts = [
                    (float(pts_raw[i]) * ss, float(pts_raw[i + 1]) * ss)
                    for i in range(0, len(pts_raw) - 1, 2)
                ]
                if len(pts) >= 3:
                    draw.polygon(pts, fill=fill, outline=stroke, width=sw)

            elif tag == "line":
                x1 = float(elem.attrib.get("x1", 0)) * ss
                y1 = float(elem.attrib.get("y1", 0)) * ss
                x2 = float(elem.attrib.get("x2", 0)) * ss
                y2 = float(elem.attrib.get("y2", 0)) * ss
                if stroke:
                    draw.line([(x1, y1), (x2, y2)], fill=stroke, width=max(1, sw))
                    # Add rounded line caps if requested
                    if elem.attrib.get("stroke-linecap") == "round" and sw > 2:
                        r_cap = sw / 2.0
                        draw.ellipse([x1 - r_cap, y1 - r_cap, x1 + r_cap, y1 + r_cap], fill=stroke)
                        draw.ellipse([x2 - r_cap, y2 - r_cap, x2 + r_cap, y2 + r_cap], fill=stroke)

        return canvas.resize((vw, vh), Image.Resampling.LANCZOS)


class FrameRenderer:
    """Composites SceneState into a Pillow RGBA frame with quantized rig caching."""

    def __init__(self, assets_root: Optional[Path] = None, max_rig_cache_size: int = 1024):
        if assets_root is None:
            assets_root = Path(__file__).resolve().parent.parent.parent / "assets"
        self.rasterizer = SVGRasterizer(assets_root)
        self._rig_cache: Dict[Tuple, Image.Image] = {}
        self._max_rig_cache_size = max_rig_cache_size
        self.rig_cache_hits = 0
        self.rig_cache_misses = 0

    @staticmethod
    def _build_rig_cache_key(avatar: AvatarState) -> Tuple:
        """Create a deterministic, quantized cache key for an AvatarState rig."""
        layer_tuples = tuple(
            (
                l.name,
                l.asset_filename,
                round(l.x * 2) / 2,
                round(l.y * 2) / 2,
                round(l.scale_x, 3),
                round(l.scale_y, 3),
                round(l.rotation, 1),
                l.visible,
                round(l.opacity, 2),
                l.z_order,
            )
            for l in sorted(avatar.layers, key=lambda item: item.z_order)
        )
        return (
            avatar.character,
            round(avatar.scale, 3),
            round(avatar.rotation, 1),
            round(avatar.opacity, 2),
            layer_tuples,
        )

    def render_avatar_rig(self, avatar: AvatarState) -> Image.Image:
        """Composite the 6 layers of an avatar into a 400x500 rig canvas, then apply avatar transforms."""
        cache_key = self._build_rig_cache_key(avatar)
        if cache_key in self._rig_cache:
            self.rig_cache_hits += 1
            return self._rig_cache[cache_key]

        self.rig_cache_misses += 1
        rig_w, rig_h = self.rasterizer.RIG_SIZE
        rig_canvas = Image.new("RGBA", (rig_w, rig_h), (0, 0, 0, 0))

        cfg = get_character_rig_config(avatar.character)
        is_pixel = getattr(cfg, "is_pixel_art", False)
        rot_resample = Image.Resampling.NEAREST if is_pixel else Image.Resampling.BICUBIC
        scale_resample = Image.Resampling.NEAREST if is_pixel else Image.Resampling.BICUBIC

        for layer in sorted(avatar.layers, key=lambda l: l.z_order):
            if not layer.visible or layer.opacity <= 0.0:
                continue

            if getattr(layer, "is_prop", False):
                base_prop = self.rasterizer.load_layer_image(
                    avatar.character, layer.asset_filename, is_prop=True, is_pixel_art=is_pixel
                )
                is_right = "right" in layer.name
                hx, hy = cfg.hand_socket_right if is_right else cfg.hand_socket_left
                
                # Base scale increased so props are bold and clearly recognizable (140px default)
                # Multiplied by user-specified layer.scale_x
                user_scale = layer.scale_x if layer.scale_x > 0 else 1.0
                base_target_dim = 140.0 * user_scale
                max_dim = max(base_prop.width, base_prop.height)
                prop_scale = base_target_dim / max_dim if max_dim > 0 else 1.0
                pw = max(1, int(round(base_prop.width * prop_scale)))
                ph = max(1, int(round(base_prop.height * prop_scale)))
                scaled_prop = base_prop.resize((pw, ph), scale_resample)

                # Anchor prop onto rig canvas at hand socket
                prop_canvas = Image.new("RGBA", (rig_w, rig_h), (0, 0, 0, 0))
                # Offset so prop's center/grip rests right at hand socket
                ox = int(round(hx - pw / 2.0))
                # For sword, the hilt/grip is near the bottom (approx 80% down); for others, near center
                if "sword" in layer.asset_filename:
                    oy = int(round(hy - ph * 0.80))
                elif "mic" in layer.asset_filename:
                    oy = int(round(hy - ph * 0.60))
                else:
                    oy = int(round(hy - ph * 0.50))
                prop_canvas.paste(scaled_prop, (ox, oy), scaled_prop)

                # Apply arm's dynamic rotation around the shoulder pivot socket
                if abs(layer.rotation) > 1e-4:
                    prop_canvas = prop_canvas.rotate(
                        -layer.rotation, resample=rot_resample, center=layer.rotation_center
                    )

                # Apply layer translation (e.g. arm movement or explosion)
                if abs(layer.x) > 1e-4 or abs(layer.y) > 1e-4:
                    temp = Image.new("RGBA", (rig_w, rig_h), (0, 0, 0, 0))
                    temp.paste(prop_canvas, (int(round(layer.x)), int(round(layer.y))))
                    prop_canvas = temp

                rig_canvas.alpha_composite(prop_canvas)
                continue

            if Path(layer.asset_filename).stem in self.rasterizer.OPTIONAL_LAYER_STEMS and not self.rasterizer.has_layer_asset(avatar.character, layer.asset_filename):
                continue

            base_img = self.rasterizer.load_layer_image(
                avatar.character, layer.asset_filename, is_pixel_art=is_pixel
            )
            layer_img = base_img

            # Apply layer-local scale if non-unit
            if abs(layer.scale_x - 1.0) > 1e-4 or abs(layer.scale_y - 1.0) > 1e-4:
                nw = max(1, int(round(rig_w * layer.scale_x)))
                nh = max(1, int(round(rig_h * layer.scale_y)))
                scaled = layer_img.resize((nw, nh), scale_resample)
                temp = Image.new("RGBA", (rig_w, rig_h), (0, 0, 0, 0))
                ox = (rig_w - nw) // 2
                oy = (rig_h - nh) // 2
                temp.paste(scaled, (ox, oy))
                layer_img = temp

            # Apply layer-local rotation if non-zero
            if abs(layer.rotation) > 1e-4:
                layer_img = layer_img.rotate(
                    -layer.rotation, resample=rot_resample, center=layer.rotation_center
                )

            # Apply layer-local translation (x, y)
            if abs(layer.x) > 1e-4 or abs(layer.y) > 1e-4:
                temp = Image.new("RGBA", (rig_w, rig_h), (0, 0, 0, 0))
                temp.paste(layer_img, (int(round(layer.x)), int(round(layer.y))))
                layer_img = temp

            rig_canvas.alpha_composite(layer_img)

        # Apply avatar-level scale
        if abs(avatar.scale - 1.0) > 1e-4:
            sw = max(1, int(round(rig_w * avatar.scale)))
            sh = max(1, int(round(rig_h * avatar.scale)))
            rig_canvas = rig_canvas.resize((sw, sh), scale_resample)

        # Apply avatar-level rotation
        if abs(avatar.rotation) > 1e-4:
            rig_canvas = rig_canvas.rotate(
                -avatar.rotation, resample=rot_resample, expand=True
            )

        # Apply avatar-level opacity (fade)
        if avatar.opacity < 0.999:
            alpha = max(0.0, min(1.0, avatar.opacity))
            r, g, b, a = rig_canvas.split()
            a = a.point(lambda p: int(round(p * alpha)))
            rig_canvas = Image.merge("RGBA", (r, g, b, a))

        if len(self._rig_cache) >= self._max_rig_cache_size:
            oldest_key = next(iter(self._rig_cache))
            del self._rig_cache[oldest_key]
        self._rig_cache[cache_key] = rig_canvas
        return rig_canvas

    def render_frame(self, scene_state: SceneState, transparent: bool = False) -> Image.Image:
        """Render a complete SceneState into a Pillow RGBA image."""
        bg_rgba = (0, 0, 0, 0) if transparent else (parse_color(scene_state.background) or (0, 0, 0, 0))
        frame = Image.new("RGBA", (scene_state.width, scene_state.height), bg_rgba)

        for avatar in scene_state.avatars:
            if avatar.opacity <= 0.0:
                continue
            rig_img = self.render_avatar_rig(avatar)
            # Center rig at (avatar.x, avatar.y)
            paste_x = int(round(avatar.x - rig_img.width / 2.0))
            paste_y = int(round(avatar.y - rig_img.height / 2.0))

            # Non-destructive procedural aura layer behind the character
            if getattr(avatar, "aura", None) and avatar.aura.active and avatar.aura.intensity > 0.001:
                aura_res = AuraRenderer.render_aura(rig_img, scene_state.timestamp, avatar.aura)
                if aura_res is not None:
                    aura_img, off_x, off_y = aura_res
                    frame.alpha_composite(aura_img, dest=(paste_x + off_x, paste_y + off_y))

            # Non-destructive procedural explosion fire layer behind the character
            front_explosion = None
            if getattr(avatar, "explosion", None) and avatar.explosion.active and avatar.explosion.fire:
                behind_res, front_res = ExplosionRenderer.render_explosion(
                    avatar.explosion, (avatar.x, avatar.y)
                )
                if behind_res is not None:
                    b_img, bx, by = behind_res
                    frame.alpha_composite(b_img, dest=(bx, by))
                if front_res is not None:
                    front_explosion = front_res

            frame.alpha_composite(rig_img, dest=(paste_x, paste_y))

            # Procedural explosion foreground sparks/core in front of character
            if front_explosion is not None:
                f_img, fx, fy = front_explosion
                frame.alpha_composite(f_img, dest=(fx, fy))

        return frame
