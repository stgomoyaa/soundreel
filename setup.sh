#!/usr/bin/env bash
# Setup inicial del proyecto. Correr una vez en Mac.
set -euo pipefail

# 1. Verifica deps del sistema
if ! command -v ffmpeg &> /dev/null; then
  echo "❌ falta ffmpeg. Instala con: brew install ffmpeg"
  exit 1
fi

if ! command -v python3.11 &> /dev/null && ! command -v python3 &> /dev/null; then
  echo "❌ falta python 3.11+. Instala con: brew install python@3.11"
  exit 1
fi

# 2. Virtualenv
if [ ! -d ".venv" ]; then
  echo "→ creando venv..."
  python3.11 -m venv .venv || python3 -m venv .venv
fi

source .venv/bin/activate

# 3. pip install
echo "→ instalando deps..."
pip install --upgrade pip
pip install -r requirements.txt

# Soundfile a veces necesita libsndfile
pip install soundfile

# 4. Estructura
mkdir -p secrets
mkdir -p data/raw_tracks data/processed data/videos data/thumbnails
mkdir -p assets/loops assets/fonts
mkdir -p logs

# 5. .env
if [ ! -f ".env" ]; then
  cp .env.example .env
  echo "→ .env creado. Edítalo con tus credenciales."
fi

# 6. Init DB
if grep -q "^DATABASE_URL=postgresql" .env; then
  echo "→ inicializando schema..."
  python -m src.db
else
  echo "⚠️ falta DATABASE_URL en .env. Inicializa DB después."
fi

echo "
✅ Setup OK. Próximos pasos:
  1. Edita .env con credenciales
  2. Descarga loops MP4 a assets/loops/  (30+ archivos)
  3. Descarga fuentes .ttf a assets/fonts/  (Cormorant Garamond / Playfair Display)
  4. Crea proyecto GCP y descarga client_secret.json en secrets/
  5. python -m src.youtube_uploader --auth-only
  6. Genera 80-100 tracks en Suno → data/raw_tracks/
  7. python -m src.audio_processor
  8. python -m src.video_builder --mode long --duration 3600
"
