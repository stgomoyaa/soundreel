# soundreel

A Python pipeline that automates a faceless ambient / lofi music YouTube
channel: it processes your generated audio tracks, assembles long-form
looped videos, generates thumbnails and SEO titles, and schedules daily
uploads through the YouTube Data API, with Postgres for state and optional
Telegram notifications.

It automates the repetitive production and publishing work. You still bring
your own music (e.g. generated in Suno) and your own channel.

## Output sample

Two frames from a real run of the pipeline — the kind of scene it loops into
long-form videos, and the color-graded output:

![Visual loop frame](docs/media/visual-loop-frame.png)

![Color grade sample](docs/media/grade-sample.png)

## What it does

```txt
your WAV tracks
   -> audio_processor    loudness-normalize, fades
   -> video_builder      assemble a long-form video over a looping visual
   -> thumbnail_gen      generate a thumbnail
   -> title/tags         SEO-oriented title and description
   -> youtube_uploader   upload via YouTube Data API (OAuth)
   -> orchestrator       schedule one upload per day, run due uploads,
                         send a daily Telegram report
```

State (tracks, uploads, schedule, view counts) lives in Postgres so the
pipeline is idempotent and can run unattended on a small VPS via cron.

## Stack

- Python 3.11+
- ffmpeg (system dependency)
- YouTube Data API v3 (OAuth desktop credentials)
- PostgreSQL
- Telegram Bot API (optional, for notifications)

## Requirements

You supply, per channel:

- Audio tracks (this pipeline does not generate music; feed it WAVs).
- A YouTube channel and a Google Cloud OAuth client.
- A Postgres database.
- Optionally, a Telegram bot for run summaries.

## Setup

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# fill in .env with your own credentials and channel branding
```

`.env.example` documents every variable: database URL, Telegram token,
YouTube OAuth paths, channel branding (`CHANNEL_NAME`, `CHANNEL_HANDLE`,
`CHANNEL_ARTIST`, `CHANNEL_DESCRIPTION`), asset directories, and tuning
knobs (loudness target, timezone, overlay opacity, etc.). No secrets are
committed: `.env` and `secrets/` are gitignored.

### YouTube OAuth (one time)

1. Google Cloud Console: create a project and enable "YouTube Data API v3".
2. Create an OAuth 2.0 Client ID (Desktop app) and download the JSON.
3. Save it to `secrets/client_secret.json` (gitignored).
4. Run `python -m src.youtube_uploader --auth-only` once to authorize in the
   browser; the token is cached to `secrets/token.pickle` (gitignored).

### Database

Create the `uploads` and `tracks` tables (see `migrations/` for the schema).

## Usage

```bash
# Schedule one upload per day for the next 7 days (default 21:00 local)
python -m src.orchestrator schedule --days 7

# Upload everything whose scheduled_for <= now
python -m src.orchestrator run

# Send a daily summary to Telegram
python -m src.orchestrator daily-report
```

Wire `run` and `daily-report` into cron for hands-off operation.

## Project layout

```txt
src/audio_processor.py   normalize + fade WAVs
src/image_to_loop.py     turn a still/short clip into a seamless visual loop
src/video_builder.py     compose long-form videos (multiple length modes)
src/thumbnail_gen.py     thumbnail generation
src/title_generator.py   titles from a configurable pool
src/titles_pool.py       title/tag/description building blocks
src/youtube_uploader.py  OAuth + resumable upload
src/orchestrator.py      scheduling, running, reporting
src/db.py                Postgres access
```

## Notes

This tool publishes automatically to YouTube. You are responsible for
following YouTube's terms and policies, including disclosure requirements
for AI-generated or altered content where they apply.

## License

MIT. See [LICENSE](LICENSE).
