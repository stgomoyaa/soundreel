"""
Title pool — wrapper sobre src.title_generator (DB de 28 templates × 22 slots).

Canal configurable vía CHANNEL_NAME/CHANNEL_DESCRIPTION en .env — por default apunta al
angle sad/heartbreak/post-breakup con leitmotif lluvia (ver title_generator para el detalle).
La DB tiene miles de combinaciones únicas; cada llamada a get_title() genera un
batch fresco y devuelve uno no usado.

Para descripciones y tags se mantienen las funciones get_description y get_tags
(estos son SEO-driven, no se generan procedural).
"""

from __future__ import annotations
import random

from . import title_generator


# Cache singleton de la DB (lazy load)
_DB: dict | None = None


def _db() -> dict:
    global _DB
    if _DB is None:
        _DB = title_generator.cargar_db()
    return _DB


def get_title(used_titles: set[str] | None = None) -> str:
    """
    Genera un título fresco desde la DB de templates.
    Filtra contra used_titles para no repetir.
    """
    used = used_titles or set()
    # Normaliza used para matching robusto (lowercase, strip)
    used_norm = {u.lower().strip() for u in used}

    # Pide un batch grande para tener variedad post-filtro
    batch = title_generator.generar(n=50, db=_db())
    available = [t for t in batch if t not in used_norm]
    if available:
        return random.choice(available)

    # Fallback: si todo el batch ya fue usado, devuelve uno random
    # (con > 1000 combinaciones posibles esto debería ser rarísimo)
    return random.choice(batch)


def _fmt_timestamp(seconds: int) -> str:
    """Formato H:MM:SS si >= 1hr, MM:SS si <1hr (estilo YouTube)."""
    seconds = int(max(0, seconds))
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


def get_description(
    title: str,
    tracklist: list[tuple[int, str]] | None = None,
    artist: str = "My Ambient Channel",
) -> str:
    """
    Descripción SEO-optimizada para el nicho ambient/sleep.

    tracklist: lista de (start_seconds, track_name) pairs.
        Se renderiza como `MM:SS  artist - name` líneas.
    """
    base = f"""{title}

#ambient #music #sad #playlist #darkambient #sleepmusic

ambient sleep music for overthinking, sleeping or just feeling sad :)"""

    if tracklist:
        lines = [f"{_fmt_timestamp(t)}  {artist} - {name}" for t, name in tracklist]
        base += "\n\ntracklist:\n" + "\n".join(lines)

    base += """

it would mean so much to me if you'd subscribe ❤️

ambient sleep music
insomnia relief
deep sleep music
music for overthinking
music for missing someone
music to fall asleep to
dark ambient music for sleep
sad ambient music
rain ambient
post breakup music"""
    return base


def get_tags() -> list[str]:
    """
    Tag set común en el nicho ambient/sleep/dark:
    dark ambient / dark sci fi / sleep music / heartbreak SEO.
    Mezcla "dark ambient" / "dark sci fi" / "sleep music" / heartbreak SEO.

    YouTube limita: 500 chars totales (tags con espacios cuentan envueltos
    en quotes) + 30 chars por tag individual. _safe_yt_tags() lo enforza.
    """
    raw = [
        # Core ambient (winning cluster)
        "ambient music",
        "dark ambient",
        "dark ambient music",
        "ambient music dark",
        "ambient music for sleep",
        # Dark sci fi sub-niche
        "dark sci fi ambient music",
        "dark sci fi music",
        "ambient sci fi music",
        "dark space music",
        "dark space music sleep",
        "drone ambient",
        "black ambient",
        "cyberpunk ambient",
        "ambient horror music",
        "dreamscape",
        # Sleep/insomnia crossover
        "sleep music",
        "music for sleep",
        "music for better sleep",
        # Mood
        "ambient mix",
        "dark ambient mix",
        # Heartbreak SEO (matches title pool)
        "music for missing someone",
        "post breakup music",
        "calm your heart",
        "rain ambient",
    ]
    return _safe_yt_tags(raw)


def _safe_yt_tags(
    tags: list[str], total_limit: int = 480, per_tag_limit: int = 30
) -> list[str]:
    """
    Trunca defensivamente para que YouTube acepte:
    - drop tags > per_tag_limit chars
    - drop tags al final hasta caber en total_limit (con margen vs el 500 real)
    """
    out: list[str] = []
    size = 0
    for t in tags:
        if len(t) > per_tag_limit:
            continue
        # YouTube cuenta tags con espacios envueltos en "" + comma separator
        cost = len(t) + (2 if " " in t else 0) + (1 if out else 0)
        if size + cost > total_limit:
            break
        out.append(t)
        size += cost
    return out


if __name__ == "__main__":
    print("=== sample titles (10) ===")
    used: set[str] = set()
    for _ in range(10):
        t = get_title(used)
        used.add(t)
        print(f"  {t}")
    # Combinatoria info
    db = _db()
    print(f"\ntemplates: {len(db['templates'])}")
    print(f"slots:     {len(db['slots'])}")
    print(f"static:    {len(db.get('static_titles', []))}")
