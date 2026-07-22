# Deployment Guide — Mac local + VPS DigitalOcean

## Topología

```
┌─────────────────┐         ┌─────────────────┐         ┌──────────────┐
│  Mac local      │         │  VPS $12/mes    │         │  YouTube     │
│  Santiago       │         │  DigitalOcean   │         │  Data API v3 │
├─────────────────┤  rsync  ├─────────────────┤  HTTPS  ├──────────────┤
│  Suno (manual)  │ ──────▶ │  All pipeline   │ ──────▶ │  tu canal    │
│  WAVs raw       │         │  ffmpeg encode  │         └──────────────┘
└─────────────────┘         │  cron uploads   │
                            │  Postgres conn  │ ────┐
                            └─────────────────┘     │
                                                    ▼
                                            ┌──────────────┐
                                            │  Postgres    │
                                            │  Railway     │
                                            └──────────────┘
```

**Por qué esta arquitectura**:
- Mac hace lo único no-automatizable (Suno UI manual)
- VPS hace TODO lo demás 24/7 sin importar si Mac está prendida
- Postgres Railway es shared state (ya lo tienes)

## Paso 1 — Crear droplet DigitalOcean

1. https://cloud.digitalocean.com → Create → Droplets
2. Image: **Ubuntu 24.04 LTS x64**
3. Plan: **Basic → Regular Intel → $12/mes** (2 GB RAM / 1 vCPU / 50 GB SSD)
4. Datacenter: **NYC3** o **SFO3** (menor latencia a Google Cloud APIs)
5. Authentication: **SSH key** (sube tu `~/.ssh/id_ed25519.pub` del Mac)
6. Hostname: `ambient-prod`
7. (Opcional) User Data: pega el contenido de `vps_provision.sh` aquí — corre como cloud-init automáticamente

Crear droplet. Toma 1 min en estar listo. Anota la IP pública.

## Paso 2 — Provisioning (si no usaste User Data)

```bash
# Desde Mac
scp vps_provision.sh root@<VPS_IP>:/root/
ssh root@<VPS_IP>
chmod +x vps_provision.sh
./vps_provision.sh
exit
```

Cuando termine: el script creó usuario `ambient` con sudo, hardening SSH, firewall, swap 2GB, ffmpeg + python 3.11.

## Paso 3 — Sync proyecto

```bash
# Desde Mac, en root del repo
rsync -avz \
  --exclude '.venv' \
  --exclude 'data/raw_tracks' \
  --exclude 'data/processed' \
  --exclude 'data/videos' \
  --exclude 'data/thumbnails' \
  --exclude 'secrets' \
  --exclude '.env' \
  --exclude '__pycache__' \
  --exclude '*.pyc' \
  ./ ambient@<VPS_IP>:/opt/ambient_machine/
```

Sync de secrets aparte (excluye git, etc.):
```bash
rsync -avz secrets/ ambient@<VPS_IP>:/opt/ambient_machine/secrets/
rsync -avz .env ambient@<VPS_IP>:/opt/ambient_machine/.env
```

## Paso 4 — Setup en VPS

```bash
ssh ambient@<VPS_IP>
cd /opt/ambient_machine
chmod +x setup.sh
./setup.sh
```

## Paso 5 — OAuth del canal (la parte tricky)

OAuth flow necesita callback a `localhost`. En VPS no hay browser, así que tunneleas:

```bash
# Desde Mac, en una terminal nueva
ssh -L 8080:localhost:8080 ambient@<VPS_IP>

# En esa sesión SSH:
cd /opt/ambient_machine
source .venv/bin/activate
python -m src.youtube_uploader --auth-only
```

El script va a imprimir un URL tipo `https://accounts.google.com/o/oauth2/...`. Cópialo y pégalo en el browser de tu Mac. Loguéate con el Gmail del canal configurado en `CHANNEL_NAME`, autoriza. El callback va a `localhost:8080` que está tunneleado al VPS → guarda token.

Verificación:
```bash
ls -la /opt/ambient_machine/secrets/
# Debe haber:
# client_secret.json
# token.pickle
```

## Paso 6 — Init schema Postgres

```bash
cd /opt/ambient_machine
source .venv/bin/activate
python -m src.db
# → schema OK
```

## Paso 7 — Activar cron

```bash
cd /opt/ambient_machine
crontab vps_cron.txt
crontab -l  # verificar
```

## Workflow diario (steady state)

### En Mac (15-45 min)

```bash
# 1. Sesión Suno: genera 8-12 tracks (manual en browser)
#    Descarga WAVs a ~/projects/ambient_machine/data/raw_tracks/

# 2. Push al VPS
cd ~/projects/ambient_machine
rsync -avz data/raw_tracks/ ambient@<VPS_IP>:/opt/ambient_machine/data/raw_tracks/
```

### En VPS (automático + manual occasional)

Lo automático ya está en cron. Lo manual cuando agregas tracks:

```bash
ssh ambient@<VPS_IP>
cd /opt/ambient_machine && source .venv/bin/activate

# Procesa los nuevos tracks
python -m src.audio_processor

# Build 4 videos (cubre próximos 4 días)
python -m src.video_builder --duration 3600
python -m src.video_builder --duration 3600
python -m src.video_builder --duration 3600
python -m src.video_builder --duration 3600

# Schedule próximos 4 días
python -m src.orchestrator schedule --days 4
```

Tarda ~10-15 min en VPS $12 (4 videos × ~3 min encoding cada uno).

Después, el cron hace upload automático cada hora chequeando lo que está `scheduled_for <= now`.

## Alias útiles en Mac (`~/.zshrc`)

```bash
alias ambient-sync='rsync -avz --exclude ".venv" --exclude "data" --exclude "secrets" --exclude ".env" ~/projects/ambient_machine/ ambient@<VPS_IP>:/opt/ambient_machine/'
alias ambient-push-tracks='rsync -avz ~/projects/ambient_machine/data/raw_tracks/ ambient@<VPS_IP>:/opt/ambient_machine/data/raw_tracks/'
alias ambient-ssh='ssh ambient@<VPS_IP>'
alias ambient-logs='ssh ambient@<VPS_IP> "tail -f /opt/ambient_machine/logs/cron_upload.log"'
```

## Monitoring

- **Telegram**: cada upload exitoso + fallido + daily report 23:00
- **Logs VPS**: `/opt/ambient_machine/logs/cron_upload.log`
- **YouTube Studio**: revisa CTR, retention, RPM
- **Postgres queries útiles**:

```sql
-- Status últimos 7 días
SELECT status, COUNT(*)
FROM uploads
WHERE uploaded_at >= NOW() - INTERVAL '7 days' OR status = 'pending'
GROUP BY status;

-- Próximos uploads programados
SELECT id, title, scheduled_for
FROM uploads
WHERE status = 'pending'
ORDER BY scheduled_for;

-- Tracks disponibles para usar
SELECT COUNT(*)
FROM tracks
WHERE processed_path IS NOT NULL
  AND cardinality(used_in_videos) < 2;
```

## Cost summary

| Item | USD/mes |
|---|---|
| Droplet DigitalOcean Basic 2GB | $12 |
| Suno Premier | $30 |
| DistroKid Musician Plus | $3.33 |
| Postgres Railway | (uso existente, ~$5) |
| Telegram | $0 |
| **TOTAL** | **~$50/mes** |

Margen target: revenue debe superar este costo en mes 2-3 mínimo. Si en mes 4 no estás en $300+/mes USD revenue combinado, kill switch.

## Troubleshooting común

### `ffmpeg: command not found` en VPS
```bash
sudo apt-get install -y ffmpeg
```

### Encoding muy lento / OOM
- Verifica swap activo: `swapon --show` (debe mostrar 2G)
- Sube preset: en `video_builder.py` cambia `-preset veryfast` a `-preset ultrafast` (peor compresión, más rápido)
- Considera droplet 4GB ($24/mes) si vas a hacer 2hr+ compilations

### YouTube quota exceeded
- Cada API key: 10.000 units/día = 6 uploads
- Si necesitas más por canal: crea segundo proyecto GCP y rota credenciales
- O distribuye uploads en 2 días

### Token OAuth expira / revocado
- Borra `secrets/token.pickle`
- Re-run `--auth-only` con SSH tunnel

### Cron no ejecuta
```bash
sudo systemctl status cron
grep CRON /var/log/syslog | tail
```

### Postgres connection refused
- Railway URL puede cambiar; verifica en dashboard
- Test: `psql $DATABASE_URL -c '\dt'`
