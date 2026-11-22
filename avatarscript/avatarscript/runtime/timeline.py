"""Timeline scheduling utilities for AvatarScript."""
from typing import Iterator
from avatarscript.runtime.scene import Scene, SceneState


def iter_scene_frames(scene: Scene) -> Iterator[tuple[int, float, SceneState]]:
    """Yield (frame_index, timestamp_sec, SceneState) across the scene duration."""
    total_frames = max(1, int(round(scene.duration * scene.fps)))
    for frame_idx in range(total_frames):
        t = frame_idx / float(scene.fps)
        yield frame_idx, t, scene.evaluate_at(t)
