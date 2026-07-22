"""
Genera thumbnails 1280x720 DESDE imagen de avatar.
NO añade texto — YouTube renderiza el título como metadata.

Treatment aplicado:
- Crop center 16:9
- Color grading violeta/azul (mood sad ambient)
- Film grain sutil
- Vignette
- Subtle chromatic aberration (vintage feel)
- Light grain overlay
"""
from __future__ import annotations
import os
import random
import subprocess
import tempfile
from pathlib import Path
import numpy as np
from PIL import Image, ImageFilter, ImageEnhance, ImageChops


THUMB_WIDTH = 1280
THUMB_HEIGHT = 720


def _extract_frame_from_mp4(mp4_path: Path) -> Image.Image | None:
    try:
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
            tmp_path = Path(tmp.name)
        cmd = [
            "ffmpeg", "-y", "-ss", "5",
            "-i", str(mp4_path),
            "-frames:v", "1",
            "-q:v", "2",
            str(tmp_path),
        ]
        result = subprocess.run(cmd, capture_output=True)
        if result.returncode != 0:
            return None
        img = Image.open(tmp_path).convert("RGB")
        tmp_path.unlink(missing_ok=True)
        return img
    except Exception:
        return None


def _get_background(avatar_dir: Path, loops_dir: Path) -> Image.Image:
    avatar_imgs = (
        list(avatar_dir.glob("*.jpg"))
        + list(avatar_dir.glob("*.jpeg"))
        + list(avatar_dir.glob("*.png"))
    )
    if avatar_imgs:
        return Image.open(random.choice(avatar_imgs)).convert("RGB")

    loops = list(loops_dir.glob("*.mp4"))
    if loops:
        img = _extract_frame_from_mp4(random.choice(loops))
        if img:
            return img

    # Fallback gradient violeta
    img = Image.new("RGB", (THUMB_WIDTH, THUMB_HEIGHT))
    pixels = img.load()
    for y in range(THUMB_HEIGHT):
        ratio = y / THUMB_HEIGHT
        r = int(20 + ratio * 25)
        g = int(10 + ratio * 8)
        b = int(35 + ratio * 30)
        for x in range(THUMB_WIDTH):
            pixels[x, y] = (r, g, b)
    return img


def _cover_crop(img: Image.Image, target_w: int, target_h: int) -> Image.Image:
    """Resize + center crop a target aspect ratio."""
    src_aspect = img.width / img.height
    tgt_aspect = target_w / target_h

    if src_aspect > tgt_aspect:
        new_h = target_h
        new_w = int(new_h * src_aspect)
    else:
        new_w = target_w
        new_h = int(new_w / src_aspect)

    img = img.resize((new_w, new_h), Image.LANCZOS)
    left = (new_w - target_w) // 2
    top = (new_h - target_h) // 2
    return img.crop((left, top, left + target_w, top + target_h))


def _color_grade(img: Image.Image) -> Image.Image:
    """
    Aplica grading violeta/azul típico del nicho ambient/lofi.
    - Desaturate
    - Lift shadows to blue/purple
    - Crush highlights ligeramente
    """
    arr = np.array(img).astype(np.float32) / 255.0

    # Desaturate parcial
    luma = 0.299 * arr[..., 0] + 0.587 * arr[..., 1] + 0.114 * arr[..., 2]
    luma = luma[..., np.newaxis]
    arr = arr * 0.72 + luma * 0.28

    # Color balance: shadows hacia azul/violeta
    # Shadows mask: dark areas
    shadow_mask = 1.0 - luma  # alto en sombras
    shadow_mask = shadow_mask ** 1.5

    # Push shadows red -, green --, blue ++
    arr[..., 0] += shadow_mask[..., 0] * 0.04  # leve rojo (violeta)
    arr[..., 1] -= shadow_mask[..., 0] * 0.04  # menos verde
    arr[..., 2] += shadow_mask[..., 0] * 0.10  # mucho azul

    # Highlight mask: bright areas
    highlight_mask = luma ** 2.5
    # Highlights ligeramente magenta
    arr[..., 0] += highlight_mask[..., 0] * 0.02
    arr[..., 2] += highlight_mask[..., 0] * 0.03

    # Crush ligero
    arr = np.clip(arr, 0.0, 1.0)
    arr = arr ** 1.08  # gamma curve para crush sombras

    arr = (arr * 255).clip(0, 255).astype(np.uint8)
    return Image.fromarray(arr)


def _add_grain(img: Image.Image, intensity: float = 0.04) -> Image.Image:
    """Film grain overlay."""
    arr = np.array(img).astype(np.float32) / 255.0
    noise = np.random.normal(0, intensity, arr.shape)
    arr = arr + noise
    arr = np.clip(arr, 0.0, 1.0)
    return Image.fromarray((arr * 255).astype(np.uint8))


def _add_vignette(img: Image.Image, strength: float = 0.4) -> Image.Image:
    """Vignette circular."""
    w, h = img.size
    arr = np.array(img).astype(np.float32) / 255.0

    Y, X = np.ogrid[:h, :w]
    cx, cy = w / 2, h / 2
    dist = np.sqrt((X - cx) ** 2 + (Y - cy) ** 2)
    max_dist = np.sqrt(cx ** 2 + cy ** 2)
    vignette = 1.0 - (dist / max_dist) ** 2 * strength
    vignette = np.clip(vignette, 0.0, 1.0)[..., np.newaxis]

    arr = arr * vignette
    arr = np.clip(arr, 0.0, 1.0)
    return Image.fromarray((arr * 255).astype(np.uint8))


def _chromatic_aberration(img: Image.Image, shift: int = 3) -> Image.Image:
    """Sutil chromatic aberration: shift R left, B right."""
    r, g, b = img.split()
    # Pad y crop para shift
    r_shifted = ImageChops.offset(r, -shift, 0)
    b_shifted = ImageChops.offset(b, shift, 0)
    return Image.merge("RGB", (r_shifted, g, b_shifted))


def make_thumbnail(
    title: str,  # ignorado, mantenido por compatibilidad de signature
    output_path: Path,
    avatar_dir: Path,
    loops_dir: Path,
    fonts_dir: Path,  # ignorado
) -> Path:
    """
    Genera thumbnail SIN texto. Solo treatment cinemático del avatar.
    """
    bg = _get_background(avatar_dir, loops_dir)
    bg = _cover_crop(bg, THUMB_WIDTH, THUMB_HEIGHT)

    # Color grade
    bg = _color_grade(bg)

    # Slight contrast boost
    bg = ImageEnhance.Contrast(bg).enhance(1.08)

    # Chromatic aberration sutil
    bg = _chromatic_aberration(bg, shift=2)

    # Vignette
    bg = _add_vignette(bg, strength=0.35)

    # Grain final
    bg = _add_grain(bg, intensity=0.025)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    bg.save(output_path, "PNG", quality=95)
    return output_path


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv()
    out = Path("data/thumbnails/_test.png")
    make_thumbnail(
        "test",
        out,
        avatar_dir=Path(os.getenv("AVATAR_DIR", "assets/avatar")),
        loops_dir=Path(os.getenv("LOOPS_DIR", "assets/loops")),
        fonts_dir=Path(os.getenv("FONTS_DIR", "assets/fonts")),
    )
    print(f"OK → {out}")
