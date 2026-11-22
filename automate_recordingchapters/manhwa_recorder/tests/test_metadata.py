import json

from manhwa_recorder.core.metadata_manager import MetadataManager, RecordingMetadata


def test_metadata_roundtrip(tmp_path):
    meta = RecordingMetadata(series_name="SSS-Class Suicide Hunter", chapter_number=7,
                             source_url="https://example.com/chapter/7", output_filename="chapter-007.mp4",
                             resolution="1920x1080", fps=30, duration_seconds=123.4, scroll_count=42,
                             encoding={"codec": "libx264", "crf": 18, "preset": "veryfast"})
    p = MetadataManager.write(meta, tmp_path / "Chapter-007" / "metadata.json")
    data = json.loads(p.read_text(encoding="utf-8"))
    for key in ("series_name", "chapter_number", "source_url", "recording_date", "resolution", "fps",
                "duration_seconds", "scroll_count", "encoding", "output_filename"):
        assert key in data
    assert data["chapter_number"] == 7
    assert data["encoding"]["crf"] == 18
    assert MetadataManager.read(p) == data
    assert MetadataManager.read(tmp_path / "missing.json") is None
