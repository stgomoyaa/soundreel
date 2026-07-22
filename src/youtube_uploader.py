"""
Uploader a YouTube Data API v3 con OAuth.

Primera vez (autoriza el canal configurado en CHANNEL_NAME):
    python -m src.youtube_uploader --auth-only

Subir video específico:
    python -m src.youtube_uploader --upload-id 42

Procesar pending del DB (los que tienen scheduled_for <= now):
    python -m src.youtube_uploader --process-pending
"""

from __future__ import annotations
import os
import pickle
import time
from pathlib import Path
import click
from dotenv import load_dotenv
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

from . import db, titles_pool


SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube",
]


def get_youtube_service():
    """Devuelve cliente YouTube autorizado."""
    client_secret = os.getenv("YT_CLIENT_SECRET")
    token_path = os.getenv("YT_TOKEN")

    if not client_secret or not token_path:
        raise SystemExit("falta YT_CLIENT_SECRET o YT_TOKEN en .env")

    token_path = Path(token_path)
    creds = None

    if token_path.exists():
        with open(token_path, "rb") as f:
            creds = pickle.load(f)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(client_secret, SCOPES)
            creds = flow.run_local_server(port=0)
        token_path.parent.mkdir(parents=True, exist_ok=True)
        with open(token_path, "wb") as f:
            pickle.dump(creds, f)

    return build("youtube", "v3", credentials=creds)


def upload_video(
    youtube,
    video_path: str,
    title: str,
    description: str,
    tags: list[str],
    thumbnail_path: str | None = None,
    privacy: str = "public",
    made_for_kids: bool = False,
) -> str:
    """
    Sube video con AI disclosure activado y devuelve video_id.
    """
    # AI disclosure: opt-in via env. Para música ambient artística no es
    # mandatorio (YouTube lo exige solo para contenido que engaña sobre
    # eventos/personas reales). El nicho competidor NO lo flaggea.
    ai_disclosure = os.getenv("AI_DISCLOSURE", "false").lower() == "true"

    body = {
        "snippet": {
            "title": title[:100],  # YouTube cap = 100 chars
            "description": description[:5000],
            "tags": tags,
            "categoryId": "10",  # Music
            "defaultLanguage": "en",
            "defaultAudioLanguage": "en",
        },
        "status": {
            "privacyStatus": privacy,
            "selfDeclaredMadeForKids": made_for_kids,
            "containsSyntheticMedia": ai_disclosure,
        },
    }

    media = MediaFileUpload(
        video_path,
        chunksize=8 * 1024 * 1024,  # 8 MB chunks
        resumable=True,
        mimetype="video/*",
    )

    request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media,
    )

    response = None
    while response is None:
        try:
            status, response = request.next_chunk()
            if status:
                pct = int(status.progress() * 100)
                print(f"  upload progress: {pct}%")
        except HttpError as e:
            if e.resp.status in [500, 502, 503, 504]:
                print(f"  retry tras error {e.resp.status}...")
                time.sleep(5)
                continue
            raise

    video_id = response["id"]
    print(f"✅ video_id={video_id}")

    # Thumbnail
    if thumbnail_path and Path(thumbnail_path).exists():
        try:
            youtube.thumbnails().set(
                videoId=video_id,
                media_body=MediaFileUpload(thumbnail_path),
            ).execute()
            print("  thumbnail set OK")
        except HttpError as e:
            # Necesita canal verificado para custom thumbnails
            print(f"  ⚠️  thumbnail failed (canal sin verificar?): {e}")

    return video_id


def _build_tracklist(
    track_ids: list[int], crossfade_sec: float = 4.0
) -> list[tuple[int, str]]:
    """
    Compone [(start_seconds, name), ...] basado en duraciones reales de tracks.
    El timestamp inicial es siempre 0:00; subsiguientes = sum(prev durs) - crossfade*idx.
    """
    tracks = db.get_tracks_by_ids(track_ids or [])
    out: list[tuple[int, str]] = []
    cumulative = 0.0
    for i, t in enumerate(tracks):
        # Nombre limpio: filename sin extensión
        from pathlib import Path

        name = Path(t["raw_path"]).stem
        out.append((int(cumulative), name))
        # Avanza por la duración del track menos el crossfade
        dur = t.get("duration_seconds") or 0
        cumulative += dur - (crossfade_sec if i < len(tracks) - 1 else 0)
    return out


def process_upload(youtube, upload_row: dict) -> str | None:
    try:
        # Tracklist con timestamps reales si hay >1 track (mode short/long)
        tracklist = None
        track_ids = upload_row.get("track_ids") or []
        if len(track_ids) > 1:
            tracklist = _build_tracklist(track_ids)

        artist = os.getenv("CHANNEL_ARTIST", "My Ambient Channel")
        description = titles_pool.get_description(
            upload_row["title"],
            tracklist=tracklist,
            artist=artist,
        )
        tags = titles_pool.get_tags()

        video_id = upload_video(
            youtube=youtube,
            video_path=upload_row["video_path"],
            title=upload_row["title"],
            description=description,
            tags=tags,
            thumbnail_path=upload_row["thumbnail_path"],
        )
        db.mark_uploaded(upload_row["id"], video_id)
        return video_id
    except Exception as e:
        db.mark_failed(upload_row["id"], str(e)[:2000])
        print(f"❌ upload failed: {e}")
        return None


@click.command()
@click.option("--auth-only", is_flag=True)
@click.option("--upload-id", type=int, default=None)
@click.option("--process-pending", is_flag=True)
def main(auth_only, upload_id, process_pending):
    load_dotenv()
    youtube = get_youtube_service()

    if auth_only:
        print("✅ auth OK")
        return

    if upload_id:
        # Upload manual de uno específico
        from psycopg2.extras import RealDictCursor

        with db.get_conn() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM uploads WHERE id = %s", (upload_id,))
                row = cur.fetchone()
        if not row:
            raise SystemExit(f"upload_id {upload_id} no existe")
        process_upload(youtube, row)
        return

    if process_pending:
        pending = db.get_pending_uploads()
        print(f"{len(pending)} pending")
        for row in pending:
            print(f"→ {row['title']}")
            process_upload(youtube, row)
            time.sleep(2)


if __name__ == "__main__":
    main()
