"""
Convierte imagen estática del avatar a MP4 loop animado (30-60s seamless).

Efectos aplicados:
- Ken Burns: zoom + pan suave, ciclo seamless
- Film grain overlay
- Vignette sutil
- Color grading mood (desaturado, warm shadows)

Uso:
    python -m src.image_to_loop --input assets/avatar/girl_01.jpg --duration 60
    python -m src.image_to_loop --batch  # procesa todo assets/avatar/ → assets/loops/
"""
from __future__ import annotations
import os
import subprocess
from pathlib import Path
import click
from dotenv import load_dotenv


def _run(cmd: list[str]) -> None:
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg failed:\n{result.stderr[-2500:]}")


def animate_image(
    input_path: Path,
    output_path: Path,
    duration: int = 60,
    width: int = 1920,
    height: int = 1080,
    fps: int = 24,
) -> None:
    """
    Toma imagen estática y produce MP4 loop seamless con:
    - Ken Burns suave (zoom in/out cycle de `duration` seg)
    - Grain overlay
    - Vignette
    - Color grading desaturado
    
    La imagen debe ser >= 2x el target output para zoom sin pérdida.
    Recomendado: input 4K (3840x2160) o mayor.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    total_frames = duration * fps
    # Período del ciclo Ken Burns fijo a 60s (independiente del duration del output)
    # → motion lento que respira; si duration < 60s ves una fracción del ciclo
    cycle_frames = 60 * fps

    # filter_complex armado por capas:
    # 1. scale para que tenga el doble del output (room para zoom)
    # 2. zoompan con curva sinusoidal para Ken Burns seamless
    # 3. eq para color grading
    # 4. noise + vignette

    # Zoom 1.0 → 1.06 → 1.0 (amplitud sutil para "respiración" calma)
    zoom_expr = f"1+0.03*(1-cos(2*PI*on/{cycle_frames}))"
    # Pan suave horizontal: oscila ±2% width
    x_expr = f"iw/2-(iw/zoom/2)+iw*0.02*sin(2*PI*on/{cycle_frames})"
    y_expr = f"ih/2-(ih/zoom/2)+ih*0.012*sin(4*PI*on/{cycle_frames})"

    vf_chain = (
        # Pre-scale: que la entrada tenga al menos 2x el output
        f"scale={width*2}:{height*2}:force_original_aspect_ratio=increase,"
        f"crop={width*2}:{height*2},"
        # Ken Burns
        f"zoompan=z='{zoom_expr}':x='{x_expr}':y='{y_expr}':"
        f"d={total_frames}:s={width}x{height}:fps={fps},"
        # Color grading desaturado warm
        "eq=saturation=0.75:contrast=1.05:brightness=-0.03:gamma=0.95,"
        # Color balance sutil hacia azul/violeta (mood sad)
        "colorbalance=rs=0.05:gs=-0.02:bs=0.10,"
        # Grain
        "noise=alls=8:allf=t,"
        # Vignette
        "vignette=PI/5"
    )

    cmd = [
        "ffmpeg", "-y",
        "-loop", "1",
        "-i", str(input_path),
        "-vf", vf_chain,
        "-t", str(duration),
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "20",
        "-pix_fmt", "yuv420p",
        "-r", str(fps),
        "-an",  # sin audio (audio se mezcla en video_builder)
        str(output_path),
    ]
    _run(cmd)


@click.command()
@click.option("--input", "input_path", type=click.Path(exists=True, path_type=Path), default=None)
@click.option("--output", "output_path", type=click.Path(path_type=Path), default=None)
@click.option("--duration", type=int, default=60)
@click.option("--batch", is_flag=True, help="Procesa todo assets/avatar/")
def main(input_path, output_path, duration, batch):
    load_dotenv()

    if batch:
        avatar_dir = Path(os.getenv("AVATAR_DIR", "assets/avatar"))
        loops_dir = Path(os.getenv("LOOPS_DIR", "assets/loops"))
        images = (
            list(avatar_dir.glob("*.jpg"))
            + list(avatar_dir.glob("*.jpeg"))
            + list(avatar_dir.glob("*.png"))
        )
        click.echo(f"procesando {len(images)} avatars → {loops_dir}")
        for img in images:
            out = loops_dir / f"{img.stem}_loop.mp4"
            if out.exists():
                click.echo(f"skip {out.name}")
                continue
            click.echo(f"→ {img.name} → {out.name}")
            try:
                animate_image(img, out, duration=duration)
            except Exception as e:
                click.echo(f"ERR {img.name}: {e}", err=True)
        return

    if not input_path:
        raise click.UsageError("Debes pasar --input o --batch")

    output_path = output_path or Path("assets/loops") / f"{input_path.stem}_loop.mp4"
    animate_image(input_path, output_path, duration=duration)
    click.echo(f"✅ {output_path}")


if __name__ == "__main__":
    main()
