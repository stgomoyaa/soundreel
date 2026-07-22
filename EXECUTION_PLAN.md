# Plan de ejecución 14 días — tu canal

## Día 0 (HOY) — Setup técnico

**Tiempo estimado: 1.5-3 horas**

1. **Branding** (30 min)
   - Canal: define nombre y tema (ej. sleep / insomnia / ambient melancolic depressive)
   - `CHANNEL_NAME=<tu canal>`, `CHANNEL_HANDLE=@<tu_handle>`, `CHANNEL_ARTIST=<tu artista>`, `CHANNEL_DESCRIPTION=<tema/nicho>` en `.env` (ver `.env.example`)
   - Crea cuenta Gmail nueva para el canal — Google bloquea multi-channel desde misma cuenta para monetización
   - Crea canal YouTube desde ese Gmail
   - Sube banner + foto perfil (Canva templates 2560×1440 banner, 800×800 PFP)

2. **DistroKid** (20 min)
   - Decide nombre de artista (puede ser igual a `CHANNEL_NAME`)
   - Confirma plan Musician Plus activo
   - Settings → YouTube Content ID → **OPT OUT** o whitelist explícito del channel ID (esto evita que Content ID reclame tus propios videos)

3. **Google Cloud** (30 min)
   - 1 proyecto: `ambient-<tu-canal>`
   - Habilitar YouTube Data API v3
   - Crear OAuth 2.0 Client ID tipo Desktop App
   - Descargar JSON → `secrets/client_secret.json`

4. **Repo** (30 min)
   ```bash
   ./setup.sh
   # Edita .env con credenciales reales
   python -m src.db  # crea schema
   python -m src.youtube_uploader --auth-only
   ```

5. **Assets visuales** (30 min)
   - Descarga 30+ loops MP4 de Pexels (búsquedas: "dark room night", "rain window", "moon clouds", "forest fog", "lonely highway")
   - Pon todos en `assets/loops/`
   - Descarga 3 fuentes serif de Google Fonts (Cormorant Garamond, Playfair Display, EB Garamond) → `assets/fonts/`

## Día 1-2 — Generación masiva tracks

**Tiempo estimado: 3-4 horas total dividible en sesiones de 1hr**

Objetivo: **40-50 tracks de calidad** en `data/raw_tracks/` (basta para 1 canal × 30+ días)

Workflow Suno:
- 5 prompts base × 8-10 generations cada uno
- Custom mode, instrumental ON, 4 min duration
- Después de cada generation: ¿uso o descarto? Filtro mental rápido
- Descarga WAV (no MP3)
- Nombra `track_001_dark_piano.wav`, `track_002_rain_pads.wav`, etc.

Prompts probados (úsalos textual):
```
1. dark ambient piano, slow, melancholic, 60bpm, no drums, deep reverb, female vocal hums distant
2. sad cinematic strings, minimal, lonely, 65bpm, no percussion, night
3. lofi ambient guitar, reverb-heavy, slow phaser, no vocals, rain sounds subtle
4. ethereal pads, sad progression Am-F-C-G, slow attack, dream-like
5. hauntology ambient, vinyl crackle, distant piano, foggy texture, melancholy
```

Una vez tengas los tracks:
```bash
python -m src.audio_processor
```

## Día 3-4 — DistroKid uploads

**Tiempo: 1.5 horas**

- Sube 10 tracks como Singles (no Album — más metadata = más SEO)
- Release date escalonada: día 3, 5, 7, 10, 14, 21, 28, 35, 42, 49
- Esto crea drip-feed de releases en Spotify que indica "artista activo" al algoritmo
- Genres: Ambient, Electronic, Sleep
- Mood tags: Sad, Calm, Reflective

## Día 4 — Primeros builds

**Tiempo: 30-45 min + render time**

```bash
# Genera 4 videos (próximos 4 días)
python -m src.video_builder --mode long --duration 3600
python -m src.video_builder --mode long --duration 3600
python -m src.video_builder --mode long --duration 3600
python -m src.video_builder --mode long --duration 3600

# Schedule
python -m src.orchestrator schedule --days 4
```

Revisa visualmente al menos 2 antes de subir. Reproduce 1 min, asegúrate que:
- Audio normalizado bien (no clipping, no demasiado bajo)
- Visual loopea sin glitch
- Thumbnail legible

## Día 5 — Primer upload manual

**Tiempo: 20 min**

```bash
# Buscar IDs de pending
python -c "from src import db; print(db.get_pending_uploads())"

# Upload manual del primero
python -m src.youtube_uploader --upload-id <ID>
```

Después del primer upload:
- Verifica en YouTube Studio que aparezca como "Altered/synthetic content" en la sección de monetización
- Si todo OK, automatiza el resto:

```bash
# Cron en Mac (crontab -e):
0 21 * * * cd /path/to/ambient_machine && /path/to/.venv/bin/python -m src.orchestrator run >> logs/cron.log 2>&1
0 23 * * * cd /path/to/ambient_machine && /path/to/.venv/bin/python -m src.orchestrator daily-report >> logs/cron.log 2>&1
```

## Día 6-14 — Operación

**Tiempo: 20-30 min/día**

Daily routine:
- 09:00 — Check Telegram report del día anterior
- 10:00-10:45 — Generar 4-6 tracks nuevos en Suno
- 10:45 — `python -m src.audio_processor`
- Si stock < 15 tracks disponibles: generar más
- 11:00 — `python -m src.video_builder --mode long --duration 3600` × N para llenar próximos 4 días
- 11:15 — `python -m src.orchestrator schedule --days 4`
- 21:00 — Cron sube automáticamente

Cada 2-3 días:
- Upload 3-5 nuevos singles a DistroKid
- Review YouTube Studio: CTR del thumbnail, watch time, audience retention
- Si un thumbnail/título performó mal, marca el patrón mentalmente y itera

## Métricas de kill-switch

Si en **mes 2** no estás en estas condiciones, considera cerrar:

| Métrica | Threshold mínimo |
|---|---|
| Subs | 1.000+ |
| Views/mes | 50.000+ |
| Spotify monthly listeners | 500+ |
| Revenue USD/mes | $50+ |

Si en **mes 4** no estás en:

| Métrica | Threshold mínimo |
|---|---|
| Subs | 7.500+ |
| Views/mes | 400.000+ |
| Revenue USD/mes | $500+ |

→ El nicho está saturado para tu approach. Cierra y enfoca todo en Pura Fama/SMS Express.

Si estás arriba: doble down. Considera abrir un 2º canal, más cadencia, o contratar VA.
