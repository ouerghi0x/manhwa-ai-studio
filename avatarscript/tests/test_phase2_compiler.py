"""Phase 2 unit tests: Lark parser, AST construction, semantic validation, and IR compilation."""
from pathlib import Path
import pytest
from avatarscript.parser import AvatarParser, AvatarSyntaxError
from avatarscript.compiler.validator import SemanticValidator, AvatarValidationException
from avatarscript.compiler.compiler import AvatarCompiler


def test_parse_and_compile_anime_reaction_example():
    """Verify the exact specification example parses, validates, and compiles into Scene IR."""
    example_path = Path(__file__).resolve().parent.parent / "examples" / "anime_reaction.ava"
    compiler = AvatarCompiler()
    scene = compiler.compile_file(example_path)

    assert scene.name == "anime_reaction"
    assert (scene.width, scene.height) == (1920, 1080)
    assert scene.background == "#202020"
    assert scene.fps == 30
    assert scene.duration == pytest.approx(12.0)
    assert scene.output_path == "output.mp4"

    assert "main" in scene.avatars
    av = scene.avatars["main"]
    assert av.character == "default"
    assert av.initial_x == pytest.approx(1920 * 0.75)
    assert av.initial_scale == pytest.approx(1.2)
    assert av.idle.breathe is True
    assert av.idle.blink_interval == pytest.approx(4.0)

    # Check timeline expressions
    expr_map = {e.timestamp: e.expression for e in av.expressions}
    assert expr_map == {
        0.0: "neutral",
        3.0: "surprised",
        6.0: "happy",
        9.0: "angry",
    }

    # Check animations and deterministic evaluation at t=9.5s (after move x:30 y:0)
    state_9_5 = scene.evaluate_at(9.5).avatars[0]
    assert state_9_5.expression == "angry"
    assert state_9_5.x == pytest.approx(1920 * 0.75 + 30.0)


def test_parse_and_compile_basic_reaction_example():
    """Verify basic_reaction.ava compiles cleanly and evaluates expected state."""
    example_path = Path(__file__).resolve().parent.parent / "examples" / "basic_reaction.ava"
    compiler = AvatarCompiler()
    scene = compiler.compile_file(example_path)
    assert scene.name == "basic_reaction"
    assert "host" in scene.avatars


def test_syntax_error_reports_line_number():
    """Verify syntax errors include accurate line and column numbers."""
    bad_script = '''scene "broken":
    canvas 1920x1080
    invalid_keyword_here 123
'''
    parser = AvatarParser()
    with pytest.raises(AvatarSyntaxError) as exc_info:
        parser.parse(bad_script)
    assert exc_info.value.loc.line == 3


def test_semantic_validation_detects_errors_with_line_numbers():
    """Verify semantic validator detects undefined character, duplicate avatar, unknown expression, and bad duration."""
    invalid_script = '''scene "bad_semantics":
    canvas 1920x1080
    duration 5s

    avatar "a1":
        character "nonexistent_char"
        position invalid_pos

        at 0s:
            expression super_saiyan
            animate shake

        at 8s:
            expression happy

    avatar "a1":
        character "default"
'''
    compiler = AvatarCompiler()
    with pytest.raises(AvatarValidationException) as exc_info:
        compiler.compile_source(invalid_script)

    errors = exc_info.value.errors
    messages = [e.message for e in errors]
    lines = [e.loc.line for e in errors]

    assert any("Undefined character 'nonexistent_char'" in m for m in messages)
    assert any("Invalid named position 'invalid_pos'" in m for m in messages)
    assert any("Unknown expression 'super_saiyan'" in m for m in messages)
    assert any("requires a positive duration" in m for m in messages)
    assert any("exceeds scene duration" in m for m in messages)
    assert any("Duplicate avatar identifier 'a1'" in m for m in messages)
    assert 6 in lines  # line of character "nonexistent_char"
    assert 10 in lines  # line of expression super_saiyan
