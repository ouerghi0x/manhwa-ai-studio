"""Chapter folder/file layout:  output/<Series>/Chapter-007/chapter-007.mp4"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..utils.file_manager import sanitize_name, unique_path


@dataclass
class ChapterPaths:
    folder: Path
    video: Path
    metadata: Path
    log: Path

    @property
    def base_name(self) -> str:
        return self.video.stem


class ChapterManager:
    def __init__(self, output_root: Path | str):
        self.output_root = Path(output_root)

    @staticmethod
    def chapter_tag(number: int) -> str:
        return f"{number:03d}"

    def series_dir(self, series: str) -> Path:
        return self.output_root / sanitize_name(series)

    def plan(self, series: str, chapter: int, filename: str = "", container: str = "mp4") -> ChapterPaths:
        """Compute paths without creating anything. Never overwrites an existing video."""
        tag = self.chapter_tag(chapter)
        folder = self.series_dir(series) / f"Chapter-{tag}"
        stem = sanitize_name(filename) if filename.strip() else f"chapter-{tag}"
        video = unique_path(folder / f"{stem}.{container}")
        suffix = video.stem[len(stem):]  # "" or "-take2"
        return ChapterPaths(folder=folder, video=video,
                            metadata=folder / f"metadata{suffix}.json",
                            log=folder / f"recording{suffix}.log")

    def prepare(self, paths: ChapterPaths) -> ChapterPaths:
        paths.folder.mkdir(parents=True, exist_ok=True)
        return paths
