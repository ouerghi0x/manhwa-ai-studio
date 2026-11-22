"""Scene and Timeline runtime container for AvatarScript."""
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from avatarscript.runtime.avatar import AvatarState
from avatarscript.runtime.animation import AvatarTimeline


@dataclass
class SceneState:
    timestamp: float
    width: int
    height: int
    background: Optional[str]
    avatars: List[AvatarState]


@dataclass
class Scene:
    name: str
    width: int = 1920
    height: int = 1080
    background: Optional[str] = "#202020"
    fps: int = 30
    duration: float = 10.0
    output_path: Optional[str] = None
    avatars: Dict[str, AvatarTimeline] = field(default_factory=dict)

    def evaluate_at(self, t: float) -> SceneState:
        """Deterministically evaluate all avatars in the scene at timestamp t."""
        avatar_states = [
            timeline.evaluate_at(t) for timeline in self.avatars.values()
        ]
        return SceneState(
            timestamp=t,
            width=self.width,
            height=self.height,
            background=self.background,
            avatars=avatar_states,
        )
