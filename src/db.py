"""Database helpers para tracking de tracks y uploads."""
from __future__ import annotations
import os
from contextlib import contextmanager
from datetime import datetime
from typing import Generator
import psycopg2
from psycopg2.extras import RealDictCursor


DDL = """
CREATE TABLE IF NOT EXISTS tracks (
    id SERIAL PRIMARY KEY,
    raw_path TEXT NOT NULL UNIQUE,
    processed_path TEXT,
    duration_seconds FLOAT,
    used_in_videos INT[] DEFAULT '{}',
    distrokid_uploaded BOOLEAN DEFAULT FALSE,
    suno_prompt TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS uploads (
    id SERIAL PRIMARY KEY,
    channel VARCHAR(20) NOT NULL DEFAULT 'main',
    video_id VARCHAR(50),
    title TEXT NOT NULL,
    track_ids INT[],
    duration_seconds INT,
    thumbnail_path TEXT,
    video_path TEXT,
    uploaded_at TIMESTAMPTZ,
    scheduled_for TIMESTAMPTZ,
    status VARCHAR(20) DEFAULT 'pending',
    view_count INT DEFAULT 0,
    error_log TEXT
);

CREATE INDEX IF NOT EXISTS idx_uploads_status ON uploads(status);
CREATE INDEX IF NOT EXISTS idx_uploads_scheduled ON uploads(scheduled_for);
CREATE INDEX IF NOT EXISTS idx_tracks_distrokid ON tracks(distrokid_uploaded);
"""


@contextmanager
def get_conn() -> Generator[psycopg2.extensions.connection, None, None]:
    """Context manager para connection a Postgres."""
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise RuntimeError("DATABASE_URL no está seteada en .env")
    conn = psycopg2.connect(db_url)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_schema() -> None:
    """Crea tablas si no existen."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(DDL)
    print("schema OK")


def register_track(raw_path: str, suno_prompt: str | None = None) -> int:
    """Inserta track si no existe; devuelve id."""
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                INSERT INTO tracks (raw_path, suno_prompt)
                VALUES (%s, %s)
                ON CONFLICT (raw_path) DO UPDATE SET raw_path = EXCLUDED.raw_path
                RETURNING id
                """,
                (raw_path, suno_prompt),
            )
            return cur.fetchone()["id"]


def mark_processed(track_id: int, processed_path: str, duration: float) -> None:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE tracks
                SET processed_path = %s, duration_seconds = %s
                WHERE id = %s
                """,
                (processed_path, duration, track_id),
            )


def get_unused_tracks(min_duration: float = 60, limit: int = 20) -> list[dict]:
    """Devuelve tracks procesados que no han sido usados en video."""
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # max 8 reuses por track: balance entre variedad y runway con
            # catálogos chicos. Para ambient compilations los listeners no notan
            # repetición si está en orden distinto + mezclado con otros tracks.
            cur.execute(
                """
                SELECT id, processed_path, duration_seconds
                FROM tracks
                WHERE processed_path IS NOT NULL
                  AND duration_seconds >= %s
                  AND cardinality(used_in_videos) < 8
                ORDER BY cardinality(used_in_videos) ASC, created_at ASC
                LIMIT %s
                """,
                (min_duration, limit),
            )
            return list(cur.fetchall())


def register_upload(
    title: str,
    track_ids: list[int],
    duration_seconds: int,
    thumbnail_path: str,
    video_path: str,
    scheduled_for: datetime | None = None,
) -> int:
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                INSERT INTO uploads
                  (title, track_ids, duration_seconds,
                   thumbnail_path, video_path, scheduled_for, status)
                VALUES (%s, %s, %s, %s, %s, %s, 'pending')
                RETURNING id
                """,
                (title, track_ids, duration_seconds,
                 thumbnail_path, video_path, scheduled_for),
            )
            upload_id = cur.fetchone()["id"]

            # Marca tracks como usados en este video
            cur.execute(
                """
                UPDATE tracks
                SET used_in_videos = array_append(used_in_videos, %s)
                WHERE id = ANY(%s)
                """,
                (upload_id, track_ids),
            )
            return upload_id


def mark_uploaded(upload_id: int, video_id: str) -> None:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE uploads
                SET status = 'uploaded', video_id = %s, uploaded_at = NOW()
                WHERE id = %s
                """,
                (video_id, upload_id),
            )


def mark_failed(upload_id: int, error: str) -> None:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE uploads
                SET status = 'failed', error_log = %s
                WHERE id = %s
                """,
                (error, upload_id),
            )


def get_track_by_id(track_id: int) -> dict | None:
    """Devuelve fila de tracks por id, o None si no existe."""
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM tracks WHERE id = %s", (track_id,))
            return cur.fetchone()


def get_tracks_by_ids(ids: list[int]) -> list[dict]:
    """
    Devuelve filas de tracks en el ORDEN solicitado (importante para tracklist).
    Si un id no existe, se omite silenciosamente.
    """
    if not ids:
        return []
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM tracks WHERE id = ANY(%s)", (ids,))
            by_id = {row["id"]: row for row in cur.fetchall()}
    return [by_id[i] for i in ids if i in by_id]


def get_used_titles() -> set[str]:
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT title FROM uploads")
            return {row["title"] for row in cur.fetchall()}


def get_pending_uploads() -> list[dict]:
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT * FROM uploads
                WHERE status = 'pending' AND scheduled_for <= NOW()
                ORDER BY scheduled_for ASC
                """
            )
            return list(cur.fetchall())


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    init_schema()
