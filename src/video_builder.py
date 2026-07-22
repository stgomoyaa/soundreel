"""
Build videos en 3 modos (patrón común del nicho ambient/lofi):

Modo 'single' (15-25 min):
    1 track Suno extendido via loop con leve variación
    Mejor SEO para 'sad music' searches (cap 4min Suno permite 4-6 loops)
    Ejemplo tipico del nicho: track largo de ~19:22

Modo 'short' (35-50 min):
    3-5 tracks crossfaded
    Equivalente "i still see you in my dreams" 41:10

Modo 'long' (1hr-2hr):
    12-20 tracks crossfaded
    Compilations clásicas tipo "she is only a memory" 1:01

Uso:
    python -m src.video_builder --mode single   --duration 1200
    python -m src.video_builder --mode short    --duration 2700
    python -m src.video_builder --mode long     --duration 3600
"""
from __future__ import annotations
import os
import random
import subprocess
from datetime import datetime
from pathlib import Path
import click
from dotenv import load_dotenv

from . import db, titles_pool, thumbnail_gen


def _run(cmd: list[str]) -> None:
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg failed:\n{result.stderr[-2500:]}")


def build_audio_compilation(
    track_paths: list[Path],
    output_path: Path,
    crossfade_sec: float = 4.0,
) -> float:
    """Concatena WAVs con crossfade. Devuelve duración total."""
    if len(track_paths) == 1:
        cmd = [
            "ffmpeg", "-y", "-i", str(track_paths[0]),
            "-c:a", "aac", "-b:a", "192k",
            str(output_path),
        ]
        _run(cmd)
    else:
        inputs = []
        for p in track_paths:
            inputs.extend(["-i", str(p)])

        filter_parts = []
        last_label = "[0:a]"
        for i in range(1, len(track_paths)):
            new_label = f"[a{i}]"
            filter_parts.append(
                f"{last_label}[{i}:a]acrossfade=d={crossfade_sec}:c1=tri:c2=tri{new_label}"
            )
            last_label = new_label

        filter_complex = ";".join(filter_parts)

        cmd = (
            ["ffmpeg", "-y"]
            + inputs
            + [
                "-filter_complex", filter_complex,
                "-map", last_label,
                "-c:a", "aac", "-b:a", "192k",
                str(output_path),
            ]
        )
        _run(cmd)

    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(output_path)],
        capture_output=True, text=True,
    )
    return float(probe.stdout.strip())


def build_extended_single(
    track_path: Path,
    output_path: Path,
    target_duration: int,
    crossfade_sec: float = 6.0,
) -> float:
    """
    Toma 1 track de ~4 min y lo extiende a target_duration con loops crossfaded.
    Cada loop varía sutilmente (pitch shift ±2 cents, EQ subtle) para que no se sienta repetitivo.
    """
    # Calculamos cuántas copias necesitamos
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(track_path)],
        capture_output=True, text=True,
    )
    track_duration = float(probe.stdout.strip())
    copies_needed = int(target_duration / (track_duration - crossfade_sec)) + 1

    # Una sola pasada de ffmpeg con N copias del mismo input + filter
    inputs = []
    for _ in range(copies_needed):
        inputs.extend(["-i", str(track_path)])

    # Variaciones por cada copia: leve pitch + filter
    variations = []
    for i in range(copies_needed):
        # asetrate trick para pitch sutil
        pitch_cents = random.choice([-10, -5, 0, 5, 10])
        rate_mult = 2 ** (pitch_cents / 1200)
        new_rate = int(48000 * rate_mult)
        # leve highpass que varía
        hp_freq = random.choice([20, 30, 40])
        variations.append(
            f"[{i}:a]asetrate={new_rate},aresample=48000,highpass=f={hp_freq}[v{i}]"
        )

    # Crossfade chain
    crossfade_parts = []
    last_label = "[v0]"
    for i in range(1, copies_needed):
        new_label = f"[a{i}]"
        crossfade_parts.append(
            f"{last_label}[v{i}]acrossfade=d={crossfade_sec}:c1=tri:c2=tri{new_label}"
        )
        last_label = new_label

    filter_complex = ";".join(variations + crossfade_parts)

    cmd = (
        ["ffmpeg", "-y"]
        + inputs
        + [
            "-filter_complex", filter_complex,
            "-map", last_label,
            "-t", str(target_duration),
            "-c:a", "aac", "-b:a", "192k",
            str(output_path),
        ]
    )
    _run(cmd)
    return target_duration


def build_video_with_visual(
    audio_path: Path,
    visual_path: Path,
    output_path: Path,
    duration_sec: float,
    fade_in_sec: float = 2.0,
    fade_out_sec: float = 3.0,
) -> None:
    fade_out_start = max(0.0, duration_sec - fade_out_sec)
    vf = (
        f"scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,"
        f"fade=t=in:st=0:d={fade_in_sec},"
        f"fade=t=out:st={fade_out_start}:d={fade_out_sec}"
    )
    cmd = [
        "ffmpeg", "-y",
        "-stream_loop", "-1",
        "-i", str(visual_path),
        "-i", str(audio_path),
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "23",
        "-pix_fmt", "yuv420p",
        "-vf", vf,
        "-c:a", "copy",
        "-shortest",
        "-t", str(duration_sec),
        str(output_path),
    ]
    _run(cmd)


def build_video_with_overlay(
    audio_path: Path,
    visual_path: Path,
    overlay_path: Path,
    output_path: Path,
    duration_sec: float,
    opacity: float = 0.30,
    blend_mode: str = "screen",
    fade_in_sec: float = 2.0,
    fade_out_sec: float = 3.0,
) -> None:
    """
    Compone visual_loop + overlay particles (rain/snow/etc) con blend
    y aplica fade in/out al composite final.
    """
    fade_out_start = max(0.0, duration_sec - fade_out_sec)
    filter_complex = (
        # [0:v] visual loop → escala/crop a 1080p
        f"[0:v]"
        f"scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,"
        f"setsar=1[base];"
        # [1:v] overlay → unifica fps y resolución (sin Ken Burns adicional)
        f"[1:v]"
        f"fps=24,"
        f"scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,"
        f"setsar=1[overlay];"
        # blend + fade sobre el composite
        f"[base][overlay]blend=all_mode='{blend_mode}':all_opacity={opacity}[blended];"
        f"[blended]"
        f"fade=t=in:st=0:d={fade_in_sec},"
        f"fade=t=out:st={fade_out_start}:d={fade_out_sec}[out]"
    )
    cmd = [
        "ffmpeg", "-y",
        "-stream_loop", "-1", "-i", str(visual_path),
        "-stream_loop", "-1", "-i", str(overlay_path),
        "-i", str(audio_path),
        "-filter_complex", filter_complex,
        "-map", "[out]",
        "-map", "2:a",
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "23",
        "-pix_fmt", "yuv420p",
        "-c:a", "copy",
        "-shortest",
        "-t", str(duration_sec),
        str(output_path),
    ]
    _run(cmd)


# Keyword → categoría de overlay. Busca en suno_prompt (case-insensitive).
OVERLAY_KEYWORDS: dict[str, list[str]] = {
    "rain": ["rain", "raining", "rainy"],
    "snow": ["snow", "winter", "snowfall"],
    "fog": ["fog", "foggy", "mist", "misty"],
    "dust": ["dust", "vinyl crackle", "grain", "vintage"],
}


def pick_overlay_for_track(
    suno_prompt: str | None,
    overlays_dir: Path,
    default_category: str | None = None,
) -> Path | None:
    """
    Selecciona overlay según keywords en suno_prompt.
    Retorna ruta a un archivo `<categoria>*.mp4` (random si hay varios).

    Orden de resolución:
      1) Si suno_prompt matchea una categoría con archivos → esa.
      2) Si no matchea y default_category está set → archivos de esa categoría.
      3) None (sin overlay).

    Retorna None si overlays_dir no existe.
    """
    if not overlays_dir.exists():
        return None

    prompt_lower = (suno_prompt or "").lower()
    for category, keywords in OVERLAY_KEYWORDS.items():
        if any(kw in prompt_lower for kw in keywords):
            candidates = list(overlays_dir.glob(f"{category}*.mp4"))
            if candidates:
                return random.choice(candidates)

    # Fallback: default_category si está configurado
    if default_category:
        candidates = list(overlays_dir.glob(f"{default_category}*.mp4"))
        if candidates:
            return random.choice(candidates)

    return None


def get_or_create_visual_loop(loops_dir: Path, avatar_dir: Path) -> Path:
    existing = list(loops_dir.glob("*.mp4"))
    if existing:
        return random.choice(existing)

    avatar_imgs = (
        list(avatar_dir.glob("*.jpg"))
        + list(avatar_dir.glob("*.jpeg"))
        + list(avatar_dir.glob("*.png"))
    )
    if not avatar_imgs:
        raise RuntimeError(
            f"No hay loops en {loops_dir} ni avatars en {avatar_dir}. "
            "Pon imágenes y corre: python -m src.image_to_loop --batch"
        )

    from . import image_to_loop
    img = random.choice(avatar_imgs)
    out = loops_dir / f"{img.stem}_loop.mp4"
    click.echo(f"  generando loop on-fly desde {img.name}...")
    image_to_loop.animate_image(img, out, duration=60)
    return out


def pick_tracks(min_tracks: int = 1, max_tracks: int = 20) -> list[dict]:
    candidates = db.get_unused_tracks(min_duration=60, limit=100)
    if not candidates:
        raise RuntimeError("no hay tracks procesados disponibles en DB")
    random.shuffle(candidates)
    return candidates[:max_tracks]


@click.command()
@click.option("--mode", type=click.Choice(["single", "short", "long"]), default="long")
@click.option("--duration", type=int, default=None)
@click.option("--crossfade", type=float, default=4.0)
@click.option("--force-overlay", default=None,
              help="Fuerza una categoría de overlay (rain/snow/fog/dust) ignorando suno_prompt. Para testing.")
def main(mode, duration, crossfade, force_overlay):
    load_dotenv()

    # Default durations por modo. mode long = 1hr fijo (sweet spot del nicho).
    if duration is None:
        duration = {
            "single": random.randint(1140, 1500),   # 19-25 min
            "short": random.randint(2400, 3000),    # 40-50 min
            "long": 3600,                            # 1 hora fija
        }[mode]

    loops_dir = Path(os.getenv("LOOPS_DIR", "assets/loops"))
    avatar_dir = Path(os.getenv("AVATAR_DIR", "assets/avatar"))
    fonts_dir = Path(os.getenv("FONTS_DIR", "assets/fonts"))
    overlays_dir = Path(os.getenv("OVERLAYS_DIR", "assets/overlays"))
    videos_dir = Path(os.getenv("VIDEOS_DIR", "data/videos"))
    thumbnails_dir = Path(os.getenv("THUMBNAILS_DIR", "data/thumbnails"))

    overlay_opacity = float(os.getenv("OVERLAY_OPACITY", "0.30"))
    overlay_blend = os.getenv("OVERLAY_BLEND_MODE", "screen")
    fade_in_sec = float(os.getenv("FADE_IN_SEC", "2.0"))
    fade_out_sec = float(os.getenv("FADE_OUT_SEC", "3.0"))
    default_overlay = os.getenv("DEFAULT_OVERLAY") or None

    # Selección de tracks según modo
    if mode == "single":
        tracks = pick_tracks(max_tracks=1)
        click.echo(f"modo single: 1 track extendido a {duration}s")
    elif mode == "short":
        # Suno top-capa los tracks a ~4min; necesitamos ~8-12 para llenar 32-48min
        n = random.randint(8, 12)
        tracks = pick_tracks(max_tracks=n)
        click.echo(f"modo short: {len(tracks)} tracks crossfaded → {duration}s target")
    else:  # long
        # Estima cuántos tracks por duración (4 min cada uno)
        n = max(8, duration // 240 + 2)
        tracks = pick_tracks(max_tracks=n)
        click.echo(f"modo long: {len(tracks)} tracks crossfaded → {duration}s")

    if not tracks:
        raise SystemExit("no hay tracks disponibles")

    # Título
    used_titles = db.get_used_titles()
    title = titles_pool.get_title(used_titles)

    # Audio
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    audio_out = videos_dir / f"{timestamp}_{mode}.m4a"
    audio_out.parent.mkdir(parents=True, exist_ok=True)

    if mode == "single":
        actual_duration = build_extended_single(
            Path(tracks[0]["processed_path"]),
            audio_out,
            duration,
            crossfade_sec=6.0,
        )
    else:
        track_paths = [Path(t["processed_path"]) for t in tracks]
        actual_duration = build_audio_compilation(track_paths, audio_out, crossfade)

    click.echo(f"audio: {actual_duration:.0f}s → {audio_out}")

    # Visual
    visual = get_or_create_visual_loop(loops_dir, avatar_dir)
    click.echo(f"visual: {visual.name}")

    # Overlay: prioridad force_overlay > suno_prompt del primer track
    overlay: Path | None = None
    if force_overlay:
        candidates = list(overlays_dir.glob(f"{force_overlay}*.mp4"))
        if candidates:
            overlay = random.choice(candidates)
            click.echo(f"overlay forzado: {overlay.name}")
        else:
            click.echo(f"⚠️  --force-overlay={force_overlay} pero no hay {force_overlay}*.mp4 en {overlays_dir}")
    else:
        first_track = db.get_track_by_id(tracks[0]["id"])
        prompt = first_track.get("suno_prompt") if first_track else None
        overlay = pick_overlay_for_track(prompt, overlays_dir, default_category=default_overlay)
        if overlay:
            # ¿match real o fallback?
            matched_kw = any(
                kw in (prompt or "").lower()
                for kws in OVERLAY_KEYWORDS.values()
                for kw in kws
            )
            tag = "keyword match" if matched_kw else f"default={default_overlay}"
            click.echo(f"overlay ({tag}): {overlay.name}")
        else:
            click.echo("overlay: ninguno (overlays_dir vacío)")

    # Video final
    video_out = videos_dir / f"{timestamp}_{mode}.mp4"
    if overlay:
        build_video_with_overlay(
            audio_path=audio_out,
            visual_path=visual,
            overlay_path=overlay,
            output_path=video_out,
            duration_sec=actual_duration,
            opacity=overlay_opacity,
            blend_mode=overlay_blend,
            fade_in_sec=fade_in_sec,
            fade_out_sec=fade_out_sec,
        )
    else:
        build_video_with_visual(
            audio_path=audio_out,
            visual_path=visual,
            output_path=video_out,
            duration_sec=actual_duration,
            fade_in_sec=fade_in_sec,
            fade_out_sec=fade_out_sec,
        )
    click.echo(f"video: {video_out}")

    # Thumbnail (sin texto)
    thumb_out = thumbnails_dir / f"{timestamp}.png"
    thumbnail_gen.make_thumbnail(
        title, thumb_out,
        avatar_dir=avatar_dir,
        loops_dir=loops_dir,
        fonts_dir=fonts_dir,
    )

    # DB
    upload_id = db.register_upload(
        title=title,
        track_ids=[t["id"] for t in tracks],
        duration_seconds=int(actual_duration),
        thumbnail_path=str(thumb_out),
        video_path=str(video_out),
    )

    # Cleanup
    audio_out.unlink(missing_ok=True)

    click.echo(f"✅ upload_id={upload_id} title='{title}' mode={mode}")


if __name__ == "__main__":
    main()
