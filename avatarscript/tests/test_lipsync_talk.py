"""Unit tests verifying the audio-driven lip-sync viseme articulation system."""
import pytest
from pathlib import Path
from avatarscript.compiler.compiler import AvatarCompiler
from avatarscript.runtime.lipsync import AudioSpeechAnalyzer


def test_audio_speech_analyzer_envelope():
    audio_path = Path("production/voices/voice_part1.mp3")
    if not audio_path.exists():
        pytest.skip("Production voice file not found")

    env = AudioSpeechAnalyzer.load_audio_envelope(audio_path)
    assert len(env.time_points) > 100
    assert env.rms_values.max() <= 1.0
    assert env.rms_values.min() >= 0.0

    # Ensure mouth moves between neutral, happy, and surprised visemes
    mouth_visemes = {AudioSpeechAnalyzer.get_mouth_at(audio_path, t) for t in [0.0, 0.5, 1.2, 1.8, 2.5]}
    assert len(mouth_visemes) >= 2


def test_talk_statement_compilation_and_lipsync():
    code = """
scene "Lip Sync Test":
    canvas 1920x1080
    fps 30
    duration 3.0s

    avatar "Narrator":
        character "default"
        position center

        at 0.0s:
            expression neutral
            talk audio:"production/voices/voice_part1.mp3" duration 2.5s
"""
    compiler = AvatarCompiler()
    scene = compiler.compile_source(code)
    timeline = scene.avatars["Narrator"]

    assert len(timeline.talk_events) == 1
    tev = timeline.talk_events[0]
    assert tev.audio == "production/voices/voice_part1.mp3"
    assert tev.duration == 2.5

    # Check mouth layer swapping during speech
    s_talk = timeline.evaluate_at(1.5)
    mouth_layer = next(l for l in s_talk.layers if l.name == "mouth")
    assert mouth_layer.asset_filename.startswith("mouth_")

    # After speech finishes (t=2.8s), mouth returns to neutral resting pose
    s_rest = timeline.evaluate_at(2.8)
    mouth_rest = next(l for l in s_rest.layers if l.name == "mouth")
    assert mouth_rest.asset_filename == "mouth_neutral.svg"
