"""metadata.json generation."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional


@dataclass
class RecordingMetadata:
    series_name: str
    chapter_number: int
    source_url: str
    output_filename: str
    resolution: str
    fps: int
    duration_seconds: float
    scroll_count: int
    encoding: dict[str, Any]
    scroll_settings: dict[str, Any] = field(default_factory=dict)
    end_reason: str = ""
    file_size_bytes: int = 0
    recording_date: str = field(default_factory=lambda: datetime.now().astimezone().isoformat(timespec="seconds"))
    app: str = "Manhwa Recorder 1.0"


class MetadataManager:
    @staticmethod
    def write(meta: RecordingMetadata, path: Path) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(asdict(meta), indent=2, ensure_ascii=False), encoding="utf-8")
        return path

    @staticmethod
    def read(path: Path) -> Optional[dict]:
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))
