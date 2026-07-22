#!/usr/bin/env python3
"""
Analiza un archivo de audio (MP3/WAV/FLAC) y extrae features útiles
para producción musical: BPM, key, modo, energía, melodía, estructura.

Uso:
    .venv/bin/python scripts/track_analyzer.py /ruta/al/track.mp3
    .venv/bin/python scripts/track_analyzer.py /ruta/al/track.mp3 --json
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path

import librosa
import numpy as np
from scipy.stats import pearsonr


KRUMHANSL_MAJOR = np.array(
    [6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88]
)
KRUMHANSL_MINOR = np.array(
    [6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17]
)
PITCH_CLASSES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


@dataclass
class TrackAnalysis:
    file: str
    duration_s: float
    sample_rate: int
    bpm: float
    bpm_confidence: str
    key: str
    mode: str
    key_confidence: float
    loudness_db: float
    energy_rms: float
    brightness: float
    warmth: float
    dynamic_range_db: float
    onsets_per_sec: float
    segments: list[dict]


def detect_key(y, sr):
    chroma = librosa.feature.chroma_cqt(y=y, sr=sr)
    chroma_avg = chroma.mean(axis=1)
    best_corr, best_key, best_mode = -np.inf, "C", "major"
    for i in range(12):
        major_corr, _ = pearsonr(chroma_avg, np.roll(KRUMHANSL_MAJOR, i))
        minor_corr, _ = pearsonr(chroma_avg, np.roll(KRUMHANSL_MINOR, i))
        if major_corr > best_corr:
            best_corr, best_key, best_mode = major_corr, PITCH_CLASSES[i], "major"
        if minor_corr > best_corr:
            best_corr, best_key, best_mode = minor_corr, PITCH_CLASSES[i], "minor"
    return best_key, best_mode, float(best_corr)


def detect_bpm(y, sr):
    tempo, beats = librosa.beat.beat_track(y=y, sr=sr, units="time")
    tempo = float(tempo) if np.ndim(tempo) == 0 else float(tempo[0])
    if len(beats) < 4:
        return tempo, "low"
    intervals = np.diff(beats)
    cv = intervals.std() / intervals.mean() if intervals.mean() > 0 else 1.0
    if cv < 0.05:
        confidence = "high"
    elif cv < 0.15:
        confidence = "medium"
    else:
        confidence = "low"
    return tempo, confidence


def get_segments(y, sr, n_segments=6):
    chroma = librosa.feature.chroma_cqt(y=y, sr=sr)
    boundaries = librosa.segment.agglomerative(chroma, k=n_segments)
    boundary_times = librosa.frames_to_time(boundaries, sr=sr)
    return [{"segment": i + 1, "start_s": round(float(t), 2)} for i, t in enumerate(boundary_times)]


def analyze(path):
    y, sr = librosa.load(str(path), sr=None, mono=True)
    if len(y) < sr * 2:
        raise ValueError("Audio muy corto (< 2s)")
    duration = len(y) / sr

    bpm, bpm_conf = detect_bpm(y, sr)
    key, mode, key_conf = detect_key(y, sr)

    rms = librosa.feature.rms(y=y)[0]
    rms_mean = float(rms.mean())
    loudness_db = float(librosa.amplitude_to_db(np.array([rms_mean]))[0])
    rms_db = librosa.amplitude_to_db(rms + 1e-10)
    dynamic_range = float(np.percentile(rms_db, 95) - np.percentile(rms_db, 5))

    centroid = float(librosa.feature.spectral_centroid(y=y, sr=sr).mean())
    rolloff = float(librosa.feature.spectral_rolloff(y=y, sr=sr, roll_percent=0.85).mean())

    onsets = librosa.onset.onset_detect(y=y, sr=sr, units="time")
    onsets_per_sec = len(onsets) / duration

    segments = get_segments(y, sr, n_segments=min(6, int(duration / 15) + 2))

    return TrackAnalysis(
        file=str(path),
        duration_s=round(duration, 2),
        sample_rate=sr,
        bpm=round(bpm, 1),
        bpm_confidence=bpm_conf,
        key=key,
        mode=mode,
        key_confidence=round(key_conf, 3),
        loudness_db=round(loudness_db, 2),
        energy_rms=round(rms_mean, 4),
        brightness=round(centroid, 1),
        warmth=round(rolloff, 1),
        dynamic_range_db=round(dynamic_range, 2),
        onsets_per_sec=round(onsets_per_sec, 2),
        segments=segments,
    )


def main():
    p = argparse.ArgumentParser()
    p.add_argument("file", type=Path)
    p.add_argument("--json", action="store_true")
    args = p.parse_args()
    try:
        result = analyze(args.file)
    except (FileNotFoundError, ValueError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    print(json.dumps(asdict(result), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
