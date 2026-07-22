"""
Test de overlay candidates: renderiza el mismo avatar+grade+Ken Burns
con cada candidato puesto encima a 30% opacity screen blend.

Uso:
    .venv/bin/python scripts/grade_test.py
"""
from __future__ import annotations
import subprocess
from pathlib import Path

INPUT_AVATAR = Path("assets/avatar/ch1_02_bedroom.png")
OUT_DIR = Path("data/grade_comparison")
WIDTH, HEIGHT = 1920, 1080
FPS = 24
PREVIEW_DURATION = 12
KEN_BURNS_CYCLE = 60
OPACITY = 0.30
FADE_IN_SEC = 1.0
FADE_OUT_SEC = 1.5

CYCLE_FRAMES = KEN_BURNS_CYCLE * FPS

ZOOM = f"1+0.03*(1-cos(2*PI*on/{CYCLE_FRAMES}))"
X = f"iw/2-(iw/zoom/2)+iw*0.02*sin(2*PI*on/{CYCLE_FRAMES})"
Y = f"ih/2-(ih/zoom/2)+ih*0.012*sin(4*PI*on/{CYCLE_FRAMES})"

BASELINE_GRADE = (
    "eq=saturation=0.75:contrast=1.05:brightness=-0.03:gamma=0.95,"
    "colorbalance=rs=0.05:gs=-0.02:bs=0.10,"
    "noise=alls=8:allf=t,"
    "vignette=PI/5"
)

CANDIDATES = [
    ("candidateA_4k60", Path("data/grade_comparison/15415148_3840_2160_60fps.mp4")),
    ("candidateB_720p25", Path("data/grade_comparison/7043616-hd_1280_720_25fps.mp4")),
]


def render(label: str, overlay_path: Path) -> Path:
    out = OUT_DIR / f"preview_{label}.mp4"

    filter_complex = (
        # Avatar → Ken Burns + baseline grade
        f"[0:v]"
        f"scale={WIDTH*2}:{HEIGHT*2}:force_original_aspect_ratio=increase,"
        f"crop={WIDTH*2}:{HEIGHT*2},"
        f"zoompan=z='{ZOOM}':x='{X}':y='{Y}':"
        f"d={PREVIEW_DURATION*FPS}:s={WIDTH}x{HEIGHT}:fps={FPS},"
        f"{BASELINE_GRADE}"
        f"[base];"

        # Overlay → solo fps + scale + crop (sin Ken Burns)
        f"[1:v]"
        f"fps={FPS},"
        f"scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=increase,"
        f"crop={WIDTH}:{HEIGHT},"
        f"setsar=1"
        f"[overlay];"

        # Screen blend + fade in/out sobre el composite final
        f"[base][overlay]blend=all_mode='screen':all_opacity={OPACITY}[blended];"
        f"[blended]"
        f"fade=t=in:st=0:d={FADE_IN_SEC},"
        f"fade=t=out:st={PREVIEW_DURATION - FADE_OUT_SEC}:d={FADE_OUT_SEC}"
        f"[out]"
    )

    cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-i", str(INPUT_AVATAR),
        "-stream_loop", "-1", "-i", str(overlay_path),
        "-filter_complex", filter_complex,
        "-map", "[out]",
        "-t", str(PREVIEW_DURATION),
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "20",
        "-pix_fmt", "yuv420p",
        "-r", str(FPS),
        "-an",
        str(out),
    ]
    print(f"rendering {label} ({overlay_path.name})...")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg failed for {label}:\n{result.stderr[-2000:]}")
    return out


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"avatar:  {INPUT_AVATAR}")
    print(f"preview: {PREVIEW_DURATION}s @ {WIDTH}x{HEIGHT} {FPS}fps")
    print(f"opacity: {OPACITY} (screen blend)")
    print(f"Ken Burns cycle: {KEN_BURNS_CYCLE}s — solo en avatar")
    print(f"fade: in {FADE_IN_SEC}s / out {FADE_OUT_SEC}s")
    print()

    for label, overlay in CANDIDATES:
        out = render(label, overlay)
        size_mb = out.stat().st_size / 1024 / 1024
        print(f"  ✅ {out.name}  ({size_mb:.1f} MB)")

    print()
    print("=" * 55)
    print(f"  open {OUT_DIR}")
    print("=" * 55)


if __name__ == "__main__":
    main()
