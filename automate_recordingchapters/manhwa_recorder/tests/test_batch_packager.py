"""Unit tests for BatchPackager: chaptersXtoY packaging, .md generation, and publisher workflow."""
import json
from pathlib import Path

from manhwa_recorder.core.batch_packager import BatchPackager


def test_batch_packager_naming(tmp_path):
    output_root = tmp_path / "output"
    workspace_root = tmp_path / "workspace"
    output_root.mkdir()
    workspace_root.mkdir()

    packager = BatchPackager(
        series_name="SSS-Class Suicide Hunter",
        chapters=[5, 6],
        output_root=output_root,
        workspace_root=workspace_root,
    )
    assert packager.folder_name == "chapters5to6"

    packager_single = BatchPackager(
        series_name="SSS-Class Suicide Hunter",
        chapters=[7],
        output_root=output_root,
        workspace_root=workspace_root,
    )
    assert packager_single.folder_name == "chapter7"


def test_batch_packager_workflow(tmp_path):
    output_root = tmp_path / "output"
    workspace_root = tmp_path / "workspace"

    # Simulate recordings in output_root
    series_dir = output_root / "SSS-Class-Suicide-Hunter"
    for ch in (20, 21):
        ch_dir = series_dir / f"Chapter-{ch:03d}"
        ch_dir.mkdir(parents=True)
        (ch_dir / f"chapter-{ch:03d}.mp4").write_bytes(b"dummy video data")
        (ch_dir / "metadata.json").write_text('{"chapter": ' + str(ch) + '}', encoding="utf-8")
        (ch_dir / "recording.log").write_text("log data", encoding="utf-8")

    packager = BatchPackager(
        series_name="SSS-Class Suicide Hunter",
        chapters=[20, 21],
        output_root=output_root,
        workspace_root=workspace_root,
    )

    pkg_dir = packager.package()
    assert pkg_dir == workspace_root / "chapters20to21"
    assert pkg_dir.exists()

    # Check episode folders gathered
    assert (pkg_dir / "Chapter-020" / "chapter-020.mp4").exists()
    assert (pkg_dir / "Chapter-021" / "chapter-021.mp4").exists()
    assert (pkg_dir / "chapter-020.mp4").exists()
    assert (pkg_dir / "chapter-021.mp4").exists()

    # Check required .md files generated
    expected_md_files = [
        "readme.md",
        "01_story_outline.md",
        "02_complete_script.md",
        "03_voiceover_script.txt",
        "04_commentary_and_reactions.md",
        "05_chapter_analysis.md",
        "06_youtube_packaging.md",
        "07_quality_control_report.md",
        "avatar_animation_plan.md",
        "avatar_integration.md",
        "production_pipeline_blueprint.md",
    ]
    for filename in expected_md_files:
        p = pkg_dir / filename
        assert p.exists(), f"Missing required file: {filename}"
        assert p.stat().st_size > 0

    # Verify readme.md includes manhwa-publisher instructions
    readme_text = (pkg_dir / "readme.md").read_text(encoding="utf-8")
    assert "manhwa-publisher" in readme_text
    assert "manhwa-publisher doctor" in readme_text
    assert "manhwa-publisher validate" in readme_text
    assert "manhwa-publisher publish" in readme_text

    # Verify publishing metadata JSON exists and is valid JSON
    meta_path = pkg_dir / "youtube_publishing_metadata.json"
    assert meta_path.exists()
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    assert "title" in meta
    assert "description" in meta
    assert "tags" in meta
    assert meta["visibility"] == "private"
