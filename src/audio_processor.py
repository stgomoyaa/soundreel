"""
Procesa WAVs raw de Suno: loudness normalize, fade in/out, registra en DB.
Uso: python -m src.audio_processor
"""
from __future__ import annotations
import os
import sys
import subprocess
from pathlib import Path
import click
import numpy as np
import soundfile as sf  # pip install soundfile (incluido con librosa, o instalalo aparte)
import pyloudnorm as pyln
from dotenv import load_dotenv
from tqdm import tqdm

from . import db


def process_wav(
    input_path: Path,
    output_path: Path,
    target_lufs: float = -14.0,
    fade_in_sec: float = 1.0,
    fade_out_sec: float = 3.0,
) -> float:
    """
    Carga WAV, normaliza a target_lufs, aplica fades, guarda.
    Devuelve duración en segundos.
    """
    data, rate = sf.read(str(input_path))

    # Si es mono, convertir a stereo
    if data.ndim == 1:
        data = np.stack([data, data], axis=1)

    # Loudness normalize
    meter = pyln.Meter(rate)
    loudness = meter.integrated_loudness(data)
    normalized = pyln.normalize.loudness(data, loudness, target_lufs)

    # Fade in / out
    fade_in_samples = int(fade_in_sec * rate)
    fade_out_samples = int(fade_out_sec * rate)

    if fade_in_samples > 0:
        fade_curve = np.linspace(0, 1, fade_in_samples).reshape(-1, 1)
        normalized[:fade_in_samples] *= fade_curve

    if fade_out_samples > 0:
        fade_curve = np.linspace(1, 0, fade_out_samples).reshape(-1, 1)
        normalized[-fade_out_samples:] *= fade_curve

    # Clip a [-1, 1] por seguridad
    normalized = np.clip(normalized, -1.0, 1.0)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(output_path), normalized, rate, subtype="PCM_16")

    duration = len(data) / rate
    return duration


@click.command()
@click.option("--input-dir", default=None, help="Override RAW_TRACKS_DIR")
@click.option("--output-dir", default=None, help="Override PROCESSED_DIR")
@click.option("--target-lufs", default=None, type=float)
@click.option("--register-db", is_flag=True, default=True)
def main(input_dir, output_dir, target_lufs, register_db):
    load_dotenv()
    input_dir = Path(input_dir or os.getenv("RAW_TRACKS_DIR", "data/raw_tracks"))
    output_dir = Path(output_dir or os.getenv("PROCESSED_DIR", "data/processed"))
    target_lufs = target_lufs or float(os.getenv("TARGET_LUFS", "-14.0"))

    wavs = sorted(input_dir.glob("*.wav"))
    if not wavs:
        click.echo(f"no WAVs en {input_dir}")
        sys.exit(0)

    click.echo(f"procesando {len(wavs)} tracks → {output_dir} @ {target_lufs} LUFS")

    for wav in tqdm(wavs):
        out_path = output_dir / wav.name
        if out_path.exists():
            continue
        try:
            duration = process_wav(wav, out_path, target_lufs)
            if register_db:
                # filename normalizado como proxy de suno_prompt: permite que
                # pick_overlay_for_track matchee keywords sin prompt explícito
                prompt_proxy = wav.stem.replace("_", " ").replace("-", " ").lower()
                track_id = db.register_track(str(wav), suno_prompt=prompt_proxy)
                db.mark_processed(track_id, str(out_path), duration)
        except Exception as e:
            click.echo(f"ERR {wav.name}: {e}", err=True)


if __name__ == "__main__":
    main()
