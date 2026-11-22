"""Pygame real-time preview player for AvatarScript."""
from pathlib import Path
from typing import Optional
import pygame
from avatarscript.runtime.scene import Scene
from avatarscript.renderer.frame_renderer import FrameRenderer


def run_preview(
    scene: Scene,
    renderer: Optional[FrameRenderer] = None,
    max_seconds: Optional[float] = None,
    window_scale: float = 0.65,
) -> None:
    """Launch an interactive Pygame preview window for a Scene.

    Controls:
      - SPACE: Play / Pause
      - R: Restart (t = 0.0s)
      - LEFT / RIGHT Arrow: Scrub -0.5s / +0.5s
      - ESC or Q: Quit
    """
    if renderer is None:
        renderer = FrameRenderer()

    pygame.init()
    win_w = max(480, int(round(scene.width * window_scale)))
    win_h = max(270, int(round(scene.height * window_scale)))
    screen = pygame.display.set_mode((win_w, win_h))
    pygame.display.set_caption(f"AvatarScript Preview — {scene.name}")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("consolas", 18, bold=True)

    current_time = 0.0
    playing = True
    elapsed_wall = 0.0
    running = True

    while running:
        dt = clock.tick(scene.fps) / 1000.0
        elapsed_wall += dt

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_ESCAPE, pygame.K_q):
                    running = False
                elif event.key == pygame.K_SPACE:
                    playing = not playing
                elif event.key == pygame.K_r:
                    current_time = 0.0
                elif event.key == pygame.K_LEFT:
                    current_time = max(0.0, current_time - 0.5)
                elif event.key == pygame.K_RIGHT:
                    current_time = min(scene.duration, current_time + 0.5)

        if playing:
            current_time += dt
            if current_time >= scene.duration:
                current_time = 0.0  # loop preview seamlessly

        # Render frame deterministically at current_time
        state = scene.evaluate_at(current_time)
        pil_img = renderer.render_frame(state)
        if (pil_img.width, pil_img.height) != (win_w, win_h):
            pil_img = pil_img.resize((win_w, win_h))

        raw_bytes = pil_img.tobytes()
        surf = pygame.image.fromstring(raw_bytes, (win_w, win_h), "RGBA")
        screen.blit(surf, (0, 0))

        # Draw HUD overlay (Play/Pause state, current timestamp, controls)
        status_str = "PLAYING" if playing else "PAUSED"
        hud_text = f"[{status_str}]  t = {current_time:05.2f}s / {scene.duration:05.2f}s   (SPACE: Play/Pause | R: Restart | Q: Quit)"
        hud_bg = pygame.Surface((win_w, 34), pygame.SRCALPHA)
        hud_bg.fill((15, 15, 20, 190))
        screen.blit(hud_bg, (0, win_h - 34))
        txt_surf = font.render(hud_text, True, (240, 240, 245))
        screen.blit(txt_surf, (14, win_h - 26))

        pygame.display.flip()

        if max_seconds is not None and elapsed_wall >= max_seconds:
            running = False

    pygame.quit()
