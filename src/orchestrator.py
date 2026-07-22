"""
Orchestrator: programa uploads y notifica a Telegram.

Programar próximos N días (1 upload diario a las 21:00 local):
    python -m src.orchestrator schedule --days 7

Ejecutar uploads cuyo scheduled_for <= now:
    python -m src.orchestrator run

Notificar resumen diario a Telegram:
    python -m src.orchestrator daily-report
"""
from __future__ import annotations
import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import click
import requests
from dotenv import load_dotenv
from psycopg2.extras import RealDictCursor

from . import db, youtube_uploader


def notify_telegram(text: str) -> None:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat:
        print(text)
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat, "text": text, "parse_mode": "Markdown"},
            timeout=10,
        )
    except Exception as e:
        print(f"telegram error: {e}")


@click.group()
def cli():
    load_dotenv()


@cli.command()
@click.option("--days", default=7, type=int)
@click.option("--per-day", default=1, type=int)
def schedule(days, per_day):
    """Asigna scheduled_for a uploads pending sin scheduled_for."""
    tz = ZoneInfo(os.getenv("TIMEZONE", "America/Santiago"))
    hour = int(os.getenv("UPLOAD_HOUR_LOCAL", "21"))

    with db.get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT id, title FROM uploads
                WHERE status = 'pending' AND scheduled_for IS NULL
                ORDER BY id
                """
            )
            unscheduled = list(cur.fetchall())

    base = datetime.now(tz).replace(hour=hour, minute=0, second=0, microsecond=0)
    if base < datetime.now(tz):
        base += timedelta(days=1)

    scheduled_count = 0
    for i, row in enumerate(unscheduled[: days * per_day]):
        day_offset = i // per_day
        slot_offset = i % per_day
        # Distribuir slots dentro del día: 21:00, 21:30, etc.
        target = base + timedelta(days=day_offset, minutes=30 * slot_offset)
        with db.get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE uploads SET scheduled_for = %s WHERE id = %s",
                    (target, row["id"]),
                )
        scheduled_count += 1
        click.echo(f"#{row['id']} → {target.isoformat()}")

    notify_telegram(f"📅 *Scheduled*: {scheduled_count} uploads próximos {days} días")


@cli.command()
def run():
    """Ejecuta uploads cuyo scheduled_for <= now."""
    pending = db.get_pending_uploads()
    click.echo(f"{len(pending)} uploads listos para subir")

    if not pending:
        return

    try:
        yt = youtube_uploader.get_youtube_service()
    except Exception as e:
        notify_telegram(f"❌ *Auth failed*\n`{e}`")
        return

    for row in pending:
        try:
            video_id = youtube_uploader.process_upload(yt, row)
            if video_id:
                url = f"https://youtu.be/{video_id}"
                notify_telegram(f"✅ *Uploaded*\n*{row['title']}*\n{url}")
        except Exception as e:
            notify_telegram(f"❌ *Failed* #{row['id']}\n`{e}`")


@cli.command(name="daily-report")
def daily_report():
    """Resumen diario de status."""
    with db.get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT
                    COUNT(*) FILTER (WHERE status = 'uploaded') AS uploaded,
                    COUNT(*) FILTER (WHERE status = 'pending') AS pending,
                    COUNT(*) FILTER (WHERE status = 'failed') AS failed
                FROM uploads
                WHERE uploaded_at >= NOW() - INTERVAL '24 hours'
                   OR status = 'pending'
                """
            )
            s = cur.fetchone()

    lines = [
        "📊 *Daily report*\n",
        f"{s['uploaded']} up · {s['pending']} pend · {s['failed']} fail",
    ]

    # Tracks disponibles
    with db.get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT COUNT(*) AS available
                FROM tracks
                WHERE processed_path IS NOT NULL
                  AND cardinality(used_in_videos) < 2
                """
            )
            available = cur.fetchone()["available"]

    lines.append(f"\n🎵 tracks disponibles: {available}")
    if available < 30:
        lines.append("⚠️ generar más tracks en Suno")

    notify_telegram("\n".join(lines))


if __name__ == "__main__":
    cli()
