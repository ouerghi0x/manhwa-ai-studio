"""Phase 5 automated tests: CLI diagnostics, rig cache performance/determinism, and full feature coverage."""
from pathlib import Path
import subprocess
import sys
import numpy as np
from avatarscript.compiler.compiler import AvatarCompiler
from avatarscript.renderer.frame_renderer import FrameRenderer


def test_cli_validation_error_shows_source_snippet_and_caret(tmp_path: Path):
    """Verify CLI prints line/column diagnostics with the offending source line and caret (^)."""
    bad_script = tmp_path / "broken.ava"
    bad_script.write_text(
        'scene "broken":\n'
        "    canvas 1920x1080\n"
        "    duration 5s\n"
        '    avatar "host":\n'
        '        character "default"\n'
        "        at 2s:\n"
        "            expression super_saiyan\n",
        encoding="utf-8",
    )

    res = subprocess.run(
        [sys.executable, "-m", "avatarscript.cli", "validate", str(bad_script)],
        capture_output=True,
        text=True,
    )
    assert res.returncode != 0
    assert "[Validation Error]" in res.stderr
    assert "Unknown expression 'super_saiyan'" in res.stderr
    assert "expression super_saiyan" in res.stderr
    assert "^" in res.stderr
    # Ensure pygame startup banner does not pollute stdout or stderr during validate
    assert "pygame" not in res.stdout.lower()


def test_rig_cache_hits_and_bit_identical_determinism():
    """Verify FrameRenderer caches static/repeated avatar rigs and produces bit-identical pixels."""
    script = """
scene "cache_test":
    canvas 800x600
    background "#101010"
    fps 30
    duration 4s

    avatar "host":
        character "default"
        position center
        scale 1.1

        at 0s:
            expression happy
"""
    compiler = AvatarCompiler()
    scene = compiler.compile_source(script)
    renderer = FrameRenderer()

    f1 = renderer.render_frame(scene.evaluate_at(0.5))
    assert renderer.rig_cache_misses == 1
    assert renderer.rig_cache_hits == 0

    # Evaluating at another timestamp with no active breathing/animations should hit the rig cache
    f2 = renderer.render_frame(scene.evaluate_at(1.5))
    assert renderer.rig_cache_misses == 1
    assert renderer.rig_cache_hits == 1
    assert np.array_equal(np.asarray(f1), np.asarray(f2))


def test_manhwa_commentary_shorts_example_compiles_and_renders():
    """Verify the new 9:16 60fps example exercising all 6 expressions & 6 animations compiles and renders."""
    example_path = (
        Path(__file__).resolve().parent.parent / "examples" / "manhwa_commentary_shorts.ava"
    )
    compiler = AvatarCompiler()
    scene = compiler.compile_file(example_path)

    assert scene.name == "manhwa_commentary_shorts"
    assert (scene.width, scene.height) == (1080, 1920)
    assert scene.fps == 60
    assert scene.duration == 10.0

    renderer = FrameRenderer()
    # Sample across all 6 expression blocks
    expected_expressions = [
        (0.2, "neutral"),
        (1.7, "surprised"),
        (3.4, "shocked"),
        (5.2, "sad"),
        (7.0, "angry"),
        (8.7, "happy"),
    ]
    for t, expr in expected_expressions:
        state = scene.evaluate_at(t)
        assert state.avatars[0].expression == expr
        frame = renderer.render_frame(state)
        assert frame.size == (1080, 1920)


def test_vscode_extension_grammar_snippets_and_logo_exist():
    """Verify the VS Code extension manifest, TextMate syntax grammar, snippets, and logo assets."""
    import json
    from PIL import Image

    ext_root = Path(__file__).resolve().parent.parent / "vscode-avatarscript"
    pkg_json = json.loads((ext_root / "package.json").read_text(encoding="utf-8"))
    assert pkg_json["name"] == "vscode-avatarscript"
    assert pkg_json["main"] == "./extension.js"
    assert (ext_root / "extension.js").exists()
    assert pkg_json["contributes"]["languages"][0]["extensions"] == [".ava"]
    cmd_ids = [c["command"] for c in pkg_json["contributes"]["commands"]]
    assert "avatarscript.preview" in cmd_ids
    assert "avatarscript.render" in cmd_ids
    assert "avatarscript.exportFrames" in cmd_ids
    assert "avatarscript.validate" in cmd_ids

    tm_grammar = json.loads(
        (ext_root / "syntaxes" / "avatarscript.tmLanguage.json").read_text(encoding="utf-8")
    )
    assert tm_grammar["scopeName"] == "source.avatarscript"
    assert "block-declarations" in tm_grammar["repository"]
    assert "animation-statements" in tm_grammar["repository"]

    snippets = json.loads(
        (ext_root / "snippets" / "avatarscript.snippets.json").read_text(encoding="utf-8")
    )
    assert "Scene Template (16:9 YouTube)" in snippets

    logo_png = ext_root / "icons" / "avatarscript-logo.png"
    assert logo_png.exists()
    with Image.open(logo_png) as img:
        assert img.size == (256, 256)

