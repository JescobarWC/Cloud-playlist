from __future__ import annotations

import aifc
import math
import wave
from array import array
from pathlib import Path

import pytest

from app.domain.audio_analysis import analyze_audio_file


def _sine_pcm(seconds: float = 1.0, freq: float = 440.0, sample_rate: int = 44100) -> tuple[array, int]:
    total_samples = int(seconds * sample_rate)
    data = array("h")
    for i in range(total_samples):
        value = int(22000 * math.sin(2 * math.pi * freq * (i / sample_rate)))
        data.append(value)
    return data, sample_rate


def _write_sine_wav(path: Path, seconds: float = 1.0, freq: float = 440.0, sample_rate: int = 44100) -> None:
    data, rate = _sine_pcm(seconds=seconds, freq=freq, sample_rate=sample_rate)
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(rate)
        wav.writeframes(data.tobytes())


def _write_sine_aiff(path: Path, seconds: float = 1.0, freq: float = 440.0, sample_rate: int = 44100) -> None:
    data, rate = _sine_pcm(seconds=seconds, freq=freq, sample_rate=sample_rate)
    with aifc.open(str(path), "wb") as aiff:
        aiff.setnchannels(1)
        aiff.setsampwidth(2)
        aiff.setframerate(rate)
        aiff.writeframes(data.tobytes())


def test_analyze_audio_file_returns_waveform_and_key_for_wav(tmp_path: Path) -> None:
    wav_path = tmp_path / "tone.wav"
    _write_sine_wav(wav_path, seconds=1.2, freq=440.0)

    result = analyze_audio_file(str(wav_path))

    assert result["waveform"]
    assert result["duration_seconds"] > 1
    assert result["key"] is not None


def test_analyze_audio_file_supports_aiff(tmp_path: Path) -> None:
    aiff_path = tmp_path / "tone.aiff"
    _write_sine_aiff(aiff_path, seconds=1.0, freq=220.0)

    result = analyze_audio_file(str(aiff_path))

    assert result["waveform"]
    assert result["sample_rate"] == 44100


def test_analyze_audio_file_rejects_unsupported_without_ffmpeg(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    file_path = tmp_path / "song.mp3"
    file_path.write_text("not really mp3")
    monkeypatch.setenv("PATH", "")

    with pytest.raises(ValueError, match="Install ffmpeg"):
        analyze_audio_file(str(file_path))
