# Cómo generar y subir videos

Doc operacional. Asume que setup ya está listo (.env con creds, deps instaladas en `.venv`, OAuth token presente).

## Comando rápido (90% de los casos)

**Video de 1 hora con todos los defaults:**
```bash
.venv/bin/python -m src.video_builder
```

Esto produce:
- 1hr de música (mode long, 3600s)
- ~17 tracks crossfaded random del catálogo
- Visual Ken Burns desde un avatar (loop reutilizado si ya existe)
- Overlay `rain.mp4` por default (fallback configurable en `.env`)
- Fade in 2s / out 3s
- Título random del generator (1,052 combinaciones)
- Thumbnail con grade cinemático sin texto
- Row pending en DB lista para schedule + upload

Tiempo: ~12-20 min (ffmpeg encoding 1hr 1080p)

---

## Workflow completo: build → schedule → upload

```bash
# 1. (Si tienes WAVs nuevos) Procesa audio + registra en DB
.venv/bin/python -m src.audio_processor

# 2. Construye 1 video (mode long = 1hr default)
.venv/bin/python -m src.video_builder

# 3. Schedule: asigna scheduled_for = hoy 21:00 (o mañana si ya pasó)
.venv/bin/python -m src.orchestrator schedule --days 1

# 4a. Sube YA (test manual):
.venv/bin/python -m src.youtube_uploader --upload-id <ID>

# 4b. O deja que el cron suba a las 21:00:
.venv/bin/python -m src.orchestrator run    # corre uploads con scheduled <= now
```

Si activaste cron (`crontab vps_cron.txt`), el paso 4b corre solo cada hora.

---

## Modos de video

```bash
.venv/bin/python -m src.video_builder --mode long           # 1hr (default, recomendado)
.venv/bin/python -m src.video_builder --mode short          # 30-50min, 8-12 tracks
.venv/bin/python -m src.video_builder --mode single         # 20min, 1 track loopeado
.venv/bin/python -m src.video_builder --duration 5400       # custom: 90min
```

| Modo | Default duration | Tracks/video | Mejor para |
|---|---|---|---|
| **long** ⭐ | 3600s (1hr) | ~17 | Sweet spot del nicho (canales grandes usan 60min de forma consistente) |
| **short** | 2400-3000s (40-50min) | 8-12 | Mid-form, menos común en el nicho top |
| **single** | 1140-1500s (20-25min) | 1 (loopeado con variación) | Sub-uso de tracks, ideal cuando tienes pocas |

---

## Flags útiles

```bash
# Forzar un overlay específico (ignora keyword match + default)
.venv/bin/python -m src.video_builder --force-overlay rain
.venv/bin/python -m src.video_builder --force-overlay snow

# Cambiar duración de crossfade entre tracks
.venv/bin/python -m src.video_builder --crossfade 6.0   # default 4s

# Ver todas las opciones
.venv/bin/python -m src.video_builder --help
```

---

## Cadencia recomendada con tu catálogo actual

**Estado actual: 39 tracks procesados.**

Cada track puede aparecer hasta 8 veces antes de ser excluido (configurado en `db.py:get_unused_tracks` con `cardinality(used_in_videos) < 8`).

**Slots disponibles: 39 × 8 = 312 apariciones totales.**

### Capacidad por modo (cuántos videos puedes hacer antes de quedarte sin tracks)

| Modo | Tracks/video | Videos posibles | Runway @ 1/día | Runway @ 5/sem |
|---|---|---|---|---|
| long (1hr) | ~17 | **~18 videos** | 2.5 sem | 3.5 sem |
| short (40min) | ~10 | **~31 videos** | 4.5 sem | 6 sem |
| single (20min) | 1 | **312 videos** | ~10 meses | ~14 meses |

### Cadencia óptima para 2 meses (~60 videos)

**Si quieres puro mode long (1hr):**
- 1 video cada 3-4 días → 18 videos = 2 meses exactos
- Posteas Lun/Jue cada semana
- Audiencia entrena a esperar 2 uploads/semana

**Si quieres daily uploads (60 videos):**
Mix obligatorio porque no alcanza con solo mode long. Receta:
- **Lun/Mié/Vie**: `--mode long` (1hr) → 3/sem × 8 sem = 24 videos × 17 tracks = 408 slots ❌ excede
- Mejor:
  - **2/sem mode long** + **5/sem mode single**: 2*17 + 5*1 = 39 slots/sem × 8 = 312 slots ✓ cabe justo
  - = 16 long + 40 single en 2 meses

**Si quieres flexibilidad para 3+ meses:**
Genera **+30 tracks más en Suno** (target 70 total → 560 slots) → puro mode long 1hr daily por 1 mes, o mix flexible 3+ meses.

### Cuando se acabe el catálogo

`db.get_unused_tracks` devuelve `[]` cuando todos los tracks están saturados. El comando va a fallar con `RuntimeError: no hay tracks procesados disponibles en DB`.

**3 soluciones:**
1. **Generar más tracks** (recomendado) — sesión Suno de 1hr produce ~10-15
2. **Subir reuse limit** en `src/db.py:get_unused_tracks` de `< 8` a `< 15`
3. **Reset usage** (rompe el "no repetir" feature):
   ```sql
   UPDATE tracks SET used_in_videos = '{}';
   ```

---

## Tracks budget tracking

```bash
# Cuántos tracks tienes disponibles ahora mismo
DATABASE_URL="$(grep '^DATABASE_URL=' .env | cut -d= -f2-)" .venv/bin/python -c "
import sys; sys.path.insert(0, '.')
from src import db
with db.get_conn() as c, c.cursor() as cur:
    cur.execute('SELECT COUNT(*) FROM tracks WHERE processed_path IS NOT NULL AND cardinality(used_in_videos) < 8')
    print(f'Tracks disponibles: {cur.fetchone()[0]}')
    cur.execute('SELECT MIN(cardinality(used_in_videos)), MAX(cardinality(used_in_videos)) FROM tracks WHERE processed_path IS NOT NULL')
    mn, mx = cur.fetchone()
    print(f'Uses range: {mn} - {mx}')
"
```

---

## Troubleshooting común

| Problema | Solución |
|---|---|
| `RuntimeError: no hay tracks procesados` | Corre `python -m src.audio_processor` o genera más tracks |
| `❌ upload failed: invalidTags` | `_safe_yt_tags()` ya defiende, pero si pasa: revisar largo |
| `❌ upload failed: quotaExceeded` | YouTube cap = 10k unidades/día = 6 uploads. Espera o usa 2do proyecto GCP |
| Video aparece con "Synthetic content" en YouTube | `AI_DISCLOSURE=false` en `.env`. Para video ya subido: edit manual en YouTube Studio |
| Visual loop genera lento on-fly | Pre-genera todos los loops: `python -m src.image_to_loop --batch` |
| Encoding muy lento | Cambiar `-preset veryfast` → `-preset ultrafast` en `src/video_builder.py` (peor compresión, más rápido) |

---

## Cleanup periódico

Los archivos generados en `data/videos/` ocupan ~200-700 MB cada uno. Después de subir + verificar OK en YouTube:

```bash
# Lista uploads ya subidos (status=uploaded)
DATABASE_URL="$(grep '^DATABASE_URL=' .env | cut -d= -f2-)" .venv/bin/python -c "
import sys; sys.path.insert(0, '.')
from src import db
from psycopg2.extras import RealDictCursor
with db.get_conn() as c, c.cursor(cursor_factory=RealDictCursor) as cur:
    cur.execute(\"SELECT id, video_path, uploaded_at FROM uploads WHERE status='uploaded'\")
    for r in cur.fetchall():
        print(f'  #{r[\"id\"]}: {r[\"video_path\"]} ({r[\"uploaded_at\"]})')
"

# Borra archivos físicos (el row de DB se mantiene como historial)
# rm data/videos/*.mp4  (cuando estés listo)
```
