import pytest

from manhwa_recorder.config.settings import AppSettings, ProjectSettings, RecordingSettings
from manhwa_recorder.core.batch_manager import BatchItem, BatchManager
from manhwa_recorder.core.chapter_manager import ChapterManager
from manhwa_recorder.utils.file_manager import sanitize_name
from manhwa_recorder.utils.validators import parse_chapter_range, validate_url


def test_layout(tmp_path):
    cm = ChapterManager(tmp_path)
    p = cm.plan("SSS-Class Suicide Hunter", 7)
    assert p.folder == tmp_path / "SSS-Class-Suicide-Hunter" / "Chapter-007"
    assert p.video.name == "chapter-007.mp4"
    assert p.metadata.name == "metadata.json"
    assert p.log.name == "recording.log"
    assert not p.folder.exists()  # plan() creates nothing


def test_no_overwrite(tmp_path):
    cm = ChapterManager(tmp_path)
    p = cm.prepare(cm.plan("X", 8))
    p.video.write_bytes(b"x")
    p2 = cm.plan("X", 8)
    assert p2.video.name == "chapter-008-take2.mp4"
    assert p2.metadata.name == "metadata-take2.json"
    p2.video.write_bytes(b"x")
    assert cm.plan("X", 8).video.name == "chapter-008-take3.mp4"


def test_custom_filename_sanitized(tmp_path):
    p = ChapterManager(tmp_path).plan('My: "Series"?', 12, filename="ep 12 / final", container="mkv")
    assert p.folder.parent.name == "My-Series"
    assert p.video.name == "ep-12-final.mkv"


@pytest.mark.parametrize("raw,expected", [("a<b>c", "a-b-c"), ("  ", "untitled"), ("CON", "_CON"),
                                          ("x...", "x")])
def test_sanitize(raw, expected):
    assert sanitize_name(raw) == expected


def test_url_template():
    p = ProjectSettings(chapter_number=7)
    assert p.resolved_url().endswith("/chapter/7")
    assert ProjectSettings(chapter_url="https://a.b/c").resolved_url() == "https://a.b/c"


def test_validators():
    assert validate_url("https://asurascans.com/x") is None
    assert validate_url("ftp://x") is not None
    assert validate_url("") is not None
    assert parse_chapter_range("45-48, 50") == [45, 46, 47, 48, 50]
    assert parse_chapter_range("3-1") == [1, 2, 3]


def test_settings_validation(tmp_path):
    with pytest.raises(ValueError):
        RecordingSettings(width=1921)
    with pytest.raises(ValueError):
        RecordingSettings(preset="bogus")
    s = AppSettings()
    s.project.chapter_number = 99
    s.save(tmp_path / "s.json")
    assert AppSettings.load(tmp_path / "s.json").project.chapter_number == 99
    (tmp_path / "bad.json").write_text("{not json")
    assert AppSettings.load(tmp_path / "bad.json").project.chapter_number == 7


def test_batch_flow():
    b = BatchManager()
    b.add_range([46, 45], "https://x/{chapter}")
    assert [i.chapter for i in b.items] == [45, 46]
    assert b.start().chapter == 45
    b.mark("done", output="a.mp4")
    assert b.advance().chapter == 46
    b.mark("failed", error="boom")
    assert b.advance() is None
    assert not b.active
    assert b.summary() == "1/2 done, 1 failed"
    with pytest.raises(RuntimeError):
        BatchManager().start()
