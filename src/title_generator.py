"""
Generador de títulos estilo canales ambient/sad/lofi de YouTube.

Uso:
    python generador_titulos.py --n 200 --seed 42 --out titulos.txt
    python generador_titulos.py --n 100 --category sleep
    python generador_titulos.py --stats

Dependencias: solo stdlib.
"""
from __future__ import annotations

import argparse
import csv
import json
import random
import string
import sys
from collections import Counter
from pathlib import Path
from typing import Any

DB_PATH = Path(__file__).parent / "titles_db.json"


def cargar_db(path: Path = DB_PATH) -> dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def claves_template(pattern: str) -> list[str]:
    """Extrae los nombres de slot de un template tipo '{a} y {b}' -> ['a','b']."""
    return [fn for _, fn, _, _ in string.Formatter().parse(pattern) if fn]


def llenar(pattern: str, slots: dict[str, list[str]], rng: random.Random) -> str | None:
    """Llena un template con valores aleatorios de cada slot. None si falta slot."""
    keys = claves_template(pattern)
    valores: dict[str, str] = {}
    for k in keys:
        if k not in slots or not slots[k]:
            return None
        valores[k] = rng.choice(slots[k])
    return pattern.format(**valores)


def generar(
    n: int,
    db: dict[str, Any],
    *,
    seed: int | None = None,
    category: str | None = None,
    incluir_estaticos: bool = True,
    max_intentos_factor: int = 50,
) -> list[str]:
    """
    Genera `n` títulos únicos.

    - category: filtra templates por categoría (sleep, lost_love, memory, ...).
    - incluir_estaticos: si True, mezcla los static_titles del JSON.
    - max_intentos_factor: corta el loop tras n*factor intentos (evita infinito).
    """
    rng = random.Random(seed)
    templates: list[dict[str, Any]] = db["templates"]
    if category:
        templates = [t for t in templates if t["category"] == category]
        if not templates:
            raise ValueError(f"Sin templates para category={category!r}")
    slots: dict[str, list[str]] = db["slots"]

    patrones = [t["pattern"] for t in templates]
    pesos = [t["weight"] for t in templates]

    out: set[str] = set()

    if incluir_estaticos and not category:
        for t in db.get("static_titles", []):
            out.add(t.lower().strip())
            if len(out) >= n:
                return sorted(out)

    intentos = 0
    limite = n * max_intentos_factor
    while len(out) < n and intentos < limite:
        intentos += 1
        pattern = rng.choices(patrones, weights=pesos, k=1)[0]
        filled = llenar(pattern, slots, rng)
        if filled is None:
            continue
        out.add(filled.lower().strip())

    return sorted(out)


def stats(db: dict[str, Any]) -> None:
    print(f"Templates: {len(db['templates'])}")
    print(f"Slots: {len(db['slots'])}")
    print(f"Static titles: {len(db.get('static_titles', []))}")
    print()
    print("Capacidad combinatoria por template:")
    slots = db["slots"]
    total = 0
    cat_counts: Counter[str] = Counter()
    for t in db["templates"]:
        keys = claves_template(t["pattern"])
        combos = 1
        for k in keys:
            combos *= len(slots.get(k, [1]))
        total += combos
        cat_counts[t["category"]] += combos
        print(f"  {t['id']:24s} [{t['category']:14s}] -> {combos:>8,} combos")
    print()
    print(f"Total combinaciones únicas posibles: {total:,}")
    print()
    print("Por categoría:")
    for cat, c in cat_counts.most_common():
        print(f"  {cat:14s} {c:>10,}")


def exportar(titulos: list[str], path: Path) -> None:
    suf = path.suffix.lower()
    if suf == ".csv":
        with path.open("w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(["title"])
            for t in titulos:
                w.writerow([t])
    else:
        path.write_text("\n".join(titulos) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--n", type=int, default=50, help="cuántos títulos generar")
    p.add_argument("--seed", type=int, default=None, help="seed para reproducibilidad")
    p.add_argument("--category", type=str, default=None, help="filtra por categoría")
    p.add_argument("--out", type=Path, default=None, help="archivo de salida (.txt o .csv)")
    p.add_argument("--no-static", action="store_true", help="excluye títulos estáticos")
    p.add_argument("--stats", action="store_true", help="solo muestra estadísticas")
    p.add_argument("--db", type=Path, default=DB_PATH, help="ruta al JSON")
    args = p.parse_args(argv)

    db = cargar_db(args.db)

    if args.stats:
        stats(db)
        return 0

    titulos = generar(
        n=args.n,
        db=db,
        seed=args.seed,
        category=args.category,
        incluir_estaticos=not args.no_static,
    )

    if args.out:
        exportar(titulos, args.out)
        print(f"{len(titulos)} títulos escritos en {args.out}", file=sys.stderr)
    else:
        for t in titulos:
            print(t)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
