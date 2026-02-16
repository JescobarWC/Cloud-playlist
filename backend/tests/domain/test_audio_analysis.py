from __future__ import annotations

import math
import wave
from array import array
from pathlib import Path

import pytest

from app.domain.audio_analysis import analyze_audio_file


def _write_sine_wav(path: Path, seconds: float = 1.0, freq: float = 440.0, sample_rate: int = 44100) -> None:
    total_samples = int(seconds * sample_rate)
    data = array("h")
    for i in range(total_samples):
        value = int(22000 * math.sin(2 * math.pi * freq * (i / sample_rate)))
        data.append(value)

    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(data.tobytes())


def test_analyze_audio_file_returns_waveform_and_key(tmp_path: Path) -> None:
    wav_path = tmp_path / "tone.wav"
    _write_sine_wav(wav_path, seconds=1.2, freq=440.0)

    result = analyze_audio_file(str(wav_path))

    assert result["waveform"]
    assert result["duration_seconds"] > 1
    assert result["key"] is not None


def test_analyze_audio_file_rejects_non_wav(tmp_path: Path) -> None:
    file_path = tmp_path / "song.mp3"
    file_path.write_text("not really mp3")

    with pytest.raises(ValueError, match="Only WAV analysis is supported"):
        analyze_audio_file(str(file_path))
