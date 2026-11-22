"""Audio speech analyzer and viseme lip-sync generator for AvatarScript."""
import math
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import numpy as np


@dataclass
class SpeechEnvelope:
    """RMS energy envelope sampled at fixed intervals."""
    sample_rate_hz: int
    window_sec: float
    time_points: np.ndarray  # timestamps in seconds
    rms_values: np.ndarray   # normalized RMS (0.0 to 1.0)


class AudioSpeechAnalyzer:
    """Extracts speech energy and determines mouth visemes from an audio file."""

    _cache: Dict[str, SpeechEnvelope] = {}

    @classmethod
    def load_audio_envelope(cls, audio_path: Path, window_sec: float = 0.04) -> SpeechEnvelope:
        """Read audio file (mp3/wav/ogg) via ffmpeg and compute time-series RMS envelope."""
        cache_key = f"{audio_path}:{window_sec}"
        if cache_key in cls._cache:
            return cls._cache[cache_key]

        target_sr = 16000
        cmd = [
            "ffmpeg",
            "-v", "error",
            "-i", str(audio_path),
            "-f", "s16le",
            "-ac", "1",
            "-ar", str(target_sr),
            "-",
        ]
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        raw_bytes, _ = proc.communicate()
        if not raw_bytes:
            # Fallback for empty audio
            env = SpeechEnvelope(
                sample_rate_hz=target_sr,
                window_sec=window_sec,
                time_points=np.array([0.0]),
                rms_values=np.array([0.0]),
            )
            cls._cache[cache_key] = env
            return env

        samples = np.frombuffer(raw_bytes, dtype=np.int16).astype(np.float32) / 32768.0
        hop_size = max(1, int(target_sr * window_sec))
        num_windows = max(1, len(samples) // hop_size)

        times = np.zeros(num_windows, dtype=np.float32)
        rms = np.zeros(num_windows, dtype=np.float32)

        for i in range(num_windows):
            chunk = samples[i * hop_size : (i + 1) * hop_size]
            times[i] = i * window_sec
            val = float(np.sqrt(np.mean(chunk**2))) if len(chunk) > 0 else 0.0
            rms[i] = val

        # Normalize with noise floor threshold
        max_val = float(np.max(rms)) if len(rms) > 0 else 1.0
        if max_val > 1e-4:
            # Remove minor background hiss / noise floor
            noise_floor = np.percentile(rms, 15)
            rms = np.maximum(0.0, rms - noise_floor)
            norm_max = np.max(rms)
            if norm_max > 1e-4:
                rms = rms / norm_max

        envelope = SpeechEnvelope(
            sample_rate_hz=target_sr,
            window_sec=window_sec,
            time_points=times,
            rms_values=rms,
        )
        cls._cache[cache_key] = envelope
        return envelope

    @classmethod
    def get_mouth_at(
        cls,
        audio_path: Path,
        t_offset: float,
        threshold: float = 0.12,
        base_expression: str = "neutral",
    ) -> str:
        """Compute the mouth asset at timestamp t_offset inside the speech.
        
        Returns mouth asset name e.g. 'mouth_neutral.svg', 'mouth_happy.svg', etc.
        """
        if t_offset < 0:
            return f"mouth_{base_expression}.svg"

        envelope = cls.load_audio_envelope(audio_path)
        if len(envelope.time_points) == 0:
            return f"mouth_{base_expression}.svg"

        idx = int(round(t_offset / envelope.window_sec))
        if idx < 0 or idx >= len(envelope.rms_values):
            return f"mouth_{base_expression}.svg"

        energy = float(envelope.rms_values[idx])

        # If below speech threshold -> closed/neutral resting mouth
        if energy < threshold:
            return f"mouth_{base_expression}.svg"

        # Cadence cycling based on time to create natural vowel/syllable articulation
        syllable_phase = math.sin(t_offset * 16.0)

        if energy > 0.65:
            # High intensity / shout / emphasis
            return "mouth_surprised.svg" if syllable_phase > 0 else "mouth_happy.svg"
        elif energy > 0.35:
            # Normal speech articulation
            return "mouth_happy.svg" if syllable_phase > -0.2 else "mouth_surprised.svg"
        else:
            # Subtle low-amplitude speech
            return "mouth_happy.svg" if syllable_phase > 0.4 else f"mouth_{base_expression}.svg"
