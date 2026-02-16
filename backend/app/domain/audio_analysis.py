from __future__ import annotations

import aifc
import math
import shutil
import subprocess
import tempfile
import wave
from array import array
from pathlib import Path

NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
SUPPORTED_DIRECT_SUFFIXES = {".wav", ".aif", ".aiff"}


def _to_mono(samples: array, channels: int) -> list[float]:
    if channels == 1:
        return [float(v) for v in samples]

    mono: list[float] = []
    for i in range(0, len(samples), channels):
        frame = samples[i : i + channels]
        mono.append(sum(frame) / channels)
    return mono


def _normalize(samples: list[float]) -> list[float]:
    if not samples:
        return []
    peak = max(abs(v) for v in samples) or 1.0
    return [v / peak for v in samples]


def _waveform_envelope(samples: list[float], bins: int = 256) -> list[float]:
    if not samples:
        return []

    chunk_size = max(1, len(samples) // bins)
    envelope: list[float] = []
    for i in range(0, len(samples), chunk_size):
        chunk = samples[i : i + chunk_size]
        envelope.append(sum(abs(v) for v in chunk) / len(chunk))
    return envelope[:bins]


def _estimate_bpm(samples: list[float], sample_rate: int) -> float | None:
    if len(samples) < sample_rate:
        return None

    window = max(1, sample_rate // 10)
    energies: list[float] = []
    for i in range(0, len(samples), window):
        chunk = samples[i : i + window]
        energies.append(sum(v * v for v in chunk) / len(chunk))

    if len(energies) < 8:
        return None

    mean_energy = sum(energies) / len(energies)
    threshold = mean_energy * 1.5
    peak_positions = [i for i, e in enumerate(energies) if e > threshold]
    if len(peak_positions) < 2:
        return None

    intervals = [b - a for a, b in zip(peak_positions, peak_positions[1:]) if b > a]
    if not intervals:
        return None

    avg_interval_windows = sum(intervals) / len(intervals)
    seconds_per_beat = (avg_interval_windows * window) / sample_rate
    if seconds_per_beat <= 0:
        return None

    bpm = 60.0 / seconds_per_beat
    if 40 <= bpm <= 220:
        return round(bpm, 2)
    return None


def _dominant_frequency(samples: list[float], sample_rate: int) -> float | None:
    if not samples:
        return None

    zero_crossings = 0
    for prev, cur in zip(samples, samples[1:]):
        if (prev <= 0 < cur) or (prev >= 0 > cur):
            zero_crossings += 1

    duration_seconds = len(samples) / sample_rate
    if duration_seconds <= 0:
        return None

    return (zero_crossings / 2) / duration_seconds


def _estimate_key(samples: list[float], sample_rate: int) -> str | None:
    freq = _dominant_frequency(samples, sample_rate)
    if freq is None or freq <= 0:
        return None

    midi = round(69 + 12 * math.log2(freq / 440.0))
    note = NOTE_NAMES[midi % 12]
    octave = (midi // 12) - 1
    return f"{note}{octave}"


def _load_pcm_samples(path: Path) -> tuple[list[float], int]:
    suffix = path.suffix.lower()

    if suffix == ".wav":
        with wave.open(str(path), "rb") as audio_file:
            channels = audio_file.getnchannels()
            sample_width = audio_file.getsampwidth()
            sample_rate = audio_file.getframerate()
            total_frames = audio_file.getnframes()
            raw_frames = audio_file.readframes(total_frames)
    elif suffix in {".aif", ".aiff"}:
        with aifc.open(str(path), "rb") as audio_file:
            channels = audio_file.getnchannels()
            sample_width = audio_file.getsampwidth()
            sample_rate = audio_file.getframerate()
            total_frames = audio_file.getnframes()
            raw_frames = audio_file.readframes(total_frames)
    else:
        raise ValueError("Unsupported direct audio format")

    if sample_width != 2:
        raise ValueError("Only 16-bit PCM WAV/AIFF files are supported directly")

    samples = array("h")
    samples.frombytes(raw_frames)
    mono = _to_mono(samples, channels)
    return _normalize(mono), sample_rate


def _decode_with_ffmpeg_to_wav(path: Path) -> Path:
    if shutil.which("ffmpeg") is None:
        raise ValueError(
            "Unsupported audio format for direct analysis. Install ffmpeg to analyze non-WAV/AIFF files"
        )

    out_dir = Path(tempfile.mkdtemp(prefix="dj-analysis-"))
    out_wav = out_dir / "decoded.wav"
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(path),
        "-ac",
        "1",
        "-ar",
        "44100",
        "-sample_fmt",
        "s16",
        str(out_wav),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0 or not out_wav.exists():
        raise ValueError("ffmpeg failed to decode audio file for analysis")
    return out_wav


def analyze_audio_file(file_path: str) -> dict[str, object]:
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Audio file not found: {file_path}")

    suffix = path.suffix.lower()

    decoded_temp: Path | None = None
    if suffix in SUPPORTED_DIRECT_SUFFIXES:
        normalized, sample_rate = _load_pcm_samples(path)
    else:
        decoded_temp = _decode_with_ffmpeg_to_wav(path)
        normalized, sample_rate = _load_pcm_samples(decoded_temp)

    if decoded_temp is not None and decoded_temp.parent.exists():
        try:
            decoded_temp.unlink(missing_ok=True)
            decoded_temp.parent.rmdir()
        except OSError:
            pass

    return {
        "waveform": _waveform_envelope(normalized),
        "bpm": _estimate_bpm(normalized, sample_rate),
        "key": _estimate_key(normalized, sample_rate),
        "sample_rate": sample_rate,
        "duration_seconds": round(len(normalized) / sample_rate, 3),
    }
