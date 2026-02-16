from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path

from app.infrastructure.import_jobs_repository import DEFAULT_DB_PATH


class LibraryRepository:
    def __init__(self, db_path: Path | None = None) -> None:
        self.db_path = db_path or DEFAULT_DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize_schema()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize_schema(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS playlists (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT (datetime('now'))
                );

                CREATE TABLE IF NOT EXISTS tracks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    artist TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT (datetime('now'))
                );

                CREATE TABLE IF NOT EXISTS playlist_tracks (
                    playlist_id INTEGER NOT NULL,
                    track_id INTEGER NOT NULL,
                    position INTEGER NOT NULL,
                    PRIMARY KEY (playlist_id, track_id),
                    FOREIGN KEY (playlist_id) REFERENCES playlists(id),
                    FOREIGN KEY (track_id) REFERENCES tracks(id)
                );

                CREATE TABLE IF NOT EXISTS track_analysis (
                    track_id INTEGER PRIMARY KEY,
                    bpm REAL,
                    musical_key TEXT,
                    waveform_json TEXT NOT NULL,
                    analyzed_at TEXT NOT NULL DEFAULT (datetime('now')),
                    FOREIGN KEY (track_id) REFERENCES tracks(id)
                );

                CREATE TABLE IF NOT EXISTS playback_sessions (
                    playlist_id INTEGER PRIMARY KEY,
                    current_track_id INTEGER,
                    accumulated_seconds REAL NOT NULL DEFAULT 0,
                    started_at REAL,
                    is_playing INTEGER NOT NULL DEFAULT 0,
                    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
                    FOREIGN KEY (playlist_id) REFERENCES playlists(id),
                    FOREIGN KEY (current_track_id) REFERENCES tracks(id)
                );

                CREATE TABLE IF NOT EXISTS analysis_jobs (
                    id TEXT PRIMARY KEY,
                    playlist_id INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    total_tracks INTEGER NOT NULL DEFAULT 0,
                    analyzed_tracks INTEGER NOT NULL DEFAULT 0,
                    failed_tracks INTEGER NOT NULL DEFAULT 0,
                    error_message TEXT,
                    cancelled_at TEXT,
                    created_at TEXT NOT NULL DEFAULT (datetime('now')),
                    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
                    FOREIGN KEY (playlist_id) REFERENCES playlists(id)
                );


                CREATE TABLE IF NOT EXISTS replace_operations (
                    id TEXT PRIMARY KEY,
                    field_name TEXT NOT NULL,
                    search_text TEXT NOT NULL,
                    replace_text TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT (datetime('now'))
                );

                CREATE TABLE IF NOT EXISTS replace_changes (
                    operation_id TEXT NOT NULL,
                    track_id INTEGER NOT NULL,
                    field_name TEXT NOT NULL,
                    old_value TEXT NOT NULL,
                    new_value TEXT NOT NULL,
                    PRIMARY KEY (operation_id, track_id, field_name),
                    FOREIGN KEY (operation_id) REFERENCES replace_operations(id),
                    FOREIGN KEY (track_id) REFERENCES tracks(id)
                );
                """
            )

            existing_columns = {
                row["name"] for row in connection.execute("PRAGMA table_info(playback_sessions)").fetchall()
            }
            if "accumulated_seconds" not in existing_columns:
                connection.execute("ALTER TABLE playback_sessions ADD COLUMN accumulated_seconds REAL NOT NULL DEFAULT 0")
            if "started_at" not in existing_columns:
                connection.execute("ALTER TABLE playback_sessions ADD COLUMN started_at REAL")

            analysis_job_columns = {row["name"] for row in connection.execute("PRAGMA table_info(analysis_jobs)").fetchall()}
            if analysis_job_columns and "cancelled_at" not in analysis_job_columns:
                connection.execute("ALTER TABLE analysis_jobs ADD COLUMN cancelled_at TEXT")

            connection.commit()

    def create_playlist(self, name: str) -> int:
        with self._connect() as connection:
            cursor = connection.execute("INSERT INTO playlists (name) VALUES (?)", (name,))
            playlist_id = int(cursor.lastrowid)
            connection.execute(
                """
                INSERT OR IGNORE INTO playback_sessions
                (playlist_id, current_track_id, accumulated_seconds, started_at, is_playing)
                VALUES (?, NULL, 0, NULL, 0)
                """,
                (playlist_id,),
            )
            connection.commit()
            return playlist_id

    def add_track_to_playlist(self, playlist_id: int, title: str, artist: str, file_path: str) -> int:
        with self._connect() as connection:
            playlist = connection.execute("SELECT id FROM playlists WHERE id = ?", (playlist_id,)).fetchone()
            if playlist is None:
                raise ValueError(f"Playlist '{playlist_id}' not found")

            cursor = connection.execute(
                "INSERT INTO tracks (title, artist, file_path) VALUES (?, ?, ?)",
                (title, artist, file_path),
            )
            track_id = int(cursor.lastrowid)

            row = connection.execute(
                "SELECT COALESCE(MAX(position), 0) + 1 AS next_position FROM playlist_tracks WHERE playlist_id = ?",
                (playlist_id,),
            ).fetchone()
            next_position = int(row["next_position"])

            connection.execute(
                "INSERT INTO playlist_tracks (playlist_id, track_id, position) VALUES (?, ?, ?)",
                (playlist_id, track_id, next_position),
            )

            session = self._get_or_create_playback_session_row(connection, playlist_id)
            if session["current_track_id"] is None:
                connection.execute(
                    "UPDATE playback_sessions SET current_track_id = ?, updated_at = datetime('now') WHERE playlist_id = ?",
                    (track_id, playlist_id),
                )

            connection.commit()
            return track_id

    def get_track(self, track_id: int) -> dict[str, object] | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT id, title, artist, file_path FROM tracks WHERE id = ?",
                (track_id,),
            ).fetchone()
        if row is None:
            return None
        return {
            "id": int(row["id"]),
            "title": row["title"],
            "artist": row["artist"],
            "file_path": row["file_path"],
        }

    def save_track_analysis(self, track_id: int, bpm: float | None, musical_key: str | None, waveform_json: str) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO track_analysis (track_id, bpm, musical_key, waveform_json)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(track_id) DO UPDATE SET
                    bpm = excluded.bpm,
                    musical_key = excluded.musical_key,
                    waveform_json = excluded.waveform_json,
                    analyzed_at = datetime('now')
                """,
                (track_id, bpm, musical_key, waveform_json),
            )
            connection.commit()

    def get_playlist(self, playlist_id: int) -> dict[str, object] | None:
        with self._connect() as connection:
            playlist = connection.execute(
                "SELECT id, name FROM playlists WHERE id = ?",
                (playlist_id,),
            ).fetchone()
            if playlist is None:
                return None

            tracks = connection.execute(
                """
                SELECT t.id, t.title, t.artist, t.file_path, pt.position, ta.bpm, ta.musical_key, ta.waveform_json
                FROM playlist_tracks pt
                JOIN tracks t ON t.id = pt.track_id
                LEFT JOIN track_analysis ta ON ta.track_id = t.id
                WHERE pt.playlist_id = ?
                ORDER BY pt.position ASC
                """,
                (playlist_id,),
            ).fetchall()

        return {
            "id": int(playlist["id"]),
            "name": playlist["name"],
            "tracks": [
                {
                    "id": int(track["id"]),
                    "title": track["title"],
                    "artist": track["artist"],
                    "file_path": track["file_path"],
                    "position": int(track["position"]),
                    "analysis": {
                        "bpm": track["bpm"],
                        "key": track["musical_key"],
                        "waveform": json.loads(track["waveform_json"]),
                    }
                    if track["waveform_json"] is not None
                    else None,
                }
                for track in tracks
            ],
        }

    def get_playlist_tracks_for_analysis(self, playlist_id: int) -> list[dict[str, object]]:
        with self._connect() as connection:
            self._ensure_playlist_exists(connection, playlist_id)
            rows = connection.execute(
                """
                SELECT t.id, t.file_path
                FROM playlist_tracks pt
                JOIN tracks t ON t.id = pt.track_id
                WHERE pt.playlist_id = ?
                ORDER BY pt.position ASC
                """,
                (playlist_id,),
            ).fetchall()
        return [{"track_id": int(row["id"]), "file_path": row["file_path"]} for row in rows]

    def create_analysis_job(self, job_id: str, playlist_id: int, total_tracks: int) -> None:
        with self._connect() as connection:
            self._ensure_playlist_exists(connection, playlist_id)
            connection.execute(
                """
                INSERT INTO analysis_jobs (id, playlist_id, status, total_tracks, analyzed_tracks, failed_tracks)
                VALUES (?, ?, 'queued', ?, 0, 0)
                """,
                (job_id, playlist_id, total_tracks),
            )
            connection.commit()

    def start_analysis_job(self, job_id: str) -> None:
        with self._connect() as connection:
            connection.execute(
                "UPDATE analysis_jobs SET status = 'running', error_message = NULL, cancelled_at = NULL, updated_at = datetime('now') WHERE id = ?",
                (job_id,),
            )
            connection.commit()

    def record_analysis_job_progress(self, job_id: str, analyzed_increment: int = 0, failed_increment: int = 0) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE analysis_jobs
                SET analyzed_tracks = analyzed_tracks + ?,
                    failed_tracks = failed_tracks + ?,
                    updated_at = datetime('now')
                WHERE id = ?
                """,
                (analyzed_increment, failed_increment, job_id),
            )
            connection.commit()

    def complete_analysis_job(self, job_id: str) -> None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT failed_tracks, status FROM analysis_jobs WHERE id = ?",
                (job_id,),
            ).fetchone()
            if row is None:
                raise ValueError(f"Analysis job '{job_id}' not found")
            if row["status"] == "cancelled":
                return
            status = "completed_with_errors" if int(row["failed_tracks"]) > 0 else "completed"
            connection.execute(
                "UPDATE analysis_jobs SET status = ?, updated_at = datetime('now') WHERE id = ?",
                (status, job_id),
            )
            connection.commit()

    def fail_analysis_job(self, job_id: str, error_message: str) -> None:
        with self._connect() as connection:
            connection.execute(
                "UPDATE analysis_jobs SET status = 'failed', error_message = ?, updated_at = datetime('now') WHERE id = ?",
                (error_message, job_id),
            )
            connection.commit()

    def cancel_analysis_job(self, job_id: str) -> dict[str, object]:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT id, status FROM analysis_jobs WHERE id = ?",
                (job_id,),
            ).fetchone()
            if row is None:
                raise ValueError(f"Analysis job '{job_id}' not found")

            status = row["status"]
            if status in {"completed", "completed_with_errors", "failed", "cancelled"}:
                return {"job_id": job_id, "status": status}

            connection.execute(
                "UPDATE analysis_jobs SET status = 'cancelled', cancelled_at = datetime('now'), updated_at = datetime('now') WHERE id = ?",
                (job_id,),
            )
            connection.commit()
            return {"job_id": job_id, "status": "cancelled"}

    def is_analysis_job_cancelled(self, job_id: str) -> bool:
        with self._connect() as connection:
            row = connection.execute("SELECT status FROM analysis_jobs WHERE id = ?", (job_id,)).fetchone()
        if row is None:
            raise ValueError(f"Analysis job '{job_id}' not found")
        return row["status"] == "cancelled"

    def get_analysis_job(self, job_id: str) -> dict[str, object] | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT id, playlist_id, status, total_tracks, analyzed_tracks, failed_tracks, error_message, cancelled_at, created_at, updated_at
                FROM analysis_jobs
                WHERE id = ?
                """,
                (job_id,),
            ).fetchone()

        if row is None:
            return None

        total = int(row["total_tracks"])
        analyzed = int(row["analyzed_tracks"])
        failed = int(row["failed_tracks"])
        done = analyzed + failed

        return {
            "job_id": row["id"],
            "playlist_id": int(row["playlist_id"]),
            "status": row["status"],
            "total_tracks": total,
            "analyzed_tracks": analyzed,
            "failed_tracks": failed,
            "progress": round((done / total) * 100, 2) if total > 0 else 100.0,
            "error_message": row["error_message"],
            "cancelled_at": row["cancelled_at"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    def find_duplicate_tracks(self) -> list[dict[str, object]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT LOWER(title) AS normalized_title,
                       LOWER(artist) AS normalized_artist,
                       COUNT(*) AS track_count,
                       GROUP_CONCAT(id) AS track_ids
                FROM tracks
                GROUP BY normalized_title, normalized_artist
                HAVING COUNT(*) > 1
                ORDER BY track_count DESC, normalized_title ASC
                """
            ).fetchall()

        duplicates: list[dict[str, object]] = []
        for row in rows:
            ids = [int(item) for item in str(row["track_ids"]).split(",") if item]
            duplicates.append(
                {
                    "title": row["normalized_title"],
                    "artist": row["normalized_artist"],
                    "track_count": int(row["track_count"]),
                    "track_ids": ids,
                }
            )
        return duplicates

    def preview_find_replace(self, field_name: str, search_text: str, replace_text: str) -> list[dict[str, object]]:
        if field_name not in {"title", "artist"}:
            raise ValueError("field_name must be 'title' or 'artist'")
        if not search_text:
            raise ValueError("search_text must not be empty")

        with self._connect() as connection:
            rows = connection.execute(
                f"SELECT id, {field_name} AS old_value FROM tracks WHERE {field_name} LIKE ?",
                (f"%{search_text}%",),
            ).fetchall()

        return [
            {
                "track_id": int(row["id"]),
                "old_value": row["old_value"],
                "new_value": str(row["old_value"]).replace(search_text, replace_text),
            }
            for row in rows
        ]

    def apply_find_replace(self, operation_id: str, field_name: str, search_text: str, replace_text: str) -> dict[str, object]:
        preview = self.preview_find_replace(field_name, search_text, replace_text)

        with self._connect() as connection:
            connection.execute(
                "INSERT INTO replace_operations (id, field_name, search_text, replace_text) VALUES (?, ?, ?, ?)",
                (operation_id, field_name, search_text, replace_text),
            )
            for item in preview:
                connection.execute(
                    """
                    INSERT INTO replace_changes (operation_id, track_id, field_name, old_value, new_value)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (operation_id, item["track_id"], field_name, item["old_value"], item["new_value"]),
                )
                connection.execute(
                    f"UPDATE tracks SET {field_name} = ? WHERE id = ?",
                    (item["new_value"], item["track_id"]),
                )
            connection.commit()

        return {"operation_id": operation_id, "changed_tracks": len(preview)}

    def undo_find_replace(self, operation_id: str) -> dict[str, object]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT track_id, field_name, old_value FROM replace_changes WHERE operation_id = ?",
                (operation_id,),
            ).fetchall()
            if not rows:
                raise ValueError(f"Replace operation '{operation_id}' not found")

            for row in rows:
                field_name = row["field_name"]
                if field_name not in {"title", "artist"}:
                    continue
                connection.execute(
                    f"UPDATE tracks SET {field_name} = ? WHERE id = ?",
                    (row["old_value"], int(row["track_id"])),
                )

            connection.execute("DELETE FROM replace_changes WHERE operation_id = ?", (operation_id,))
            connection.execute("DELETE FROM replace_operations WHERE id = ?", (operation_id,))
            connection.commit()

        return {"operation_id": operation_id, "restored_tracks": len(rows)}

    def _list_playlist_track_ids(self, connection: sqlite3.Connection, playlist_id: int) -> list[int]:
        rows = connection.execute(
            "SELECT track_id FROM playlist_tracks WHERE playlist_id = ? ORDER BY position ASC",
            (playlist_id,),
        ).fetchall()
        return [int(row["track_id"]) for row in rows]

    def _ensure_playlist_exists(self, connection: sqlite3.Connection, playlist_id: int) -> None:
        row = connection.execute("SELECT id FROM playlists WHERE id = ?", (playlist_id,)).fetchone()
        if row is None:
            raise ValueError(f"Playlist '{playlist_id}' not found")

    def _get_or_create_playback_session_row(self, connection: sqlite3.Connection, playlist_id: int) -> sqlite3.Row:
        self._ensure_playlist_exists(connection, playlist_id)
        connection.execute(
            """
            INSERT OR IGNORE INTO playback_sessions
            (playlist_id, current_track_id, accumulated_seconds, started_at, is_playing)
            VALUES (?, NULL, 0, NULL, 0)
            """,
            (playlist_id,),
        )
        row = connection.execute(
            "SELECT playlist_id, current_track_id, accumulated_seconds, started_at, is_playing FROM playback_sessions WHERE playlist_id = ?",
            (playlist_id,),
        ).fetchone()
        if row is None:
            raise ValueError(f"Playback session for playlist '{playlist_id}' could not be created")
        return row

    def _compute_position_seconds(self, session: sqlite3.Row) -> float:
        accumulated = float(session["accumulated_seconds"] or 0.0)
        if not bool(session["is_playing"]):
            return accumulated

        started_at = session["started_at"]
        if started_at is None:
            return accumulated

        elapsed = max(0.0, time.time() - float(started_at))
        return accumulated + elapsed

    def get_playback_state(self, playlist_id: int) -> dict[str, object]:
        with self._connect() as connection:
            session = self._get_or_create_playback_session_row(connection, playlist_id)
            track_ids = self._list_playlist_track_ids(connection, playlist_id)

        current_track_id = session["current_track_id"]
        current_index = track_ids.index(current_track_id) if current_track_id in track_ids else None

        return {
            "playlist_id": playlist_id,
            "track_ids": track_ids,
            "current_track_id": int(current_track_id) if current_track_id is not None else None,
            "current_position_seconds": round(self._compute_position_seconds(session), 3),
            "is_playing": bool(session["is_playing"]),
            "current_index": current_index,
        }

    def set_current_track(self, playlist_id: int, track_id: int) -> dict[str, object]:
        with self._connect() as connection:
            session = self._get_or_create_playback_session_row(connection, playlist_id)
            track_ids = self._list_playlist_track_ids(connection, playlist_id)
            if track_id not in track_ids:
                raise ValueError(f"Track '{track_id}' is not in playlist '{playlist_id}'")

            new_started_at = time.time() if bool(session["is_playing"]) else None
            connection.execute(
                """
                UPDATE playback_sessions
                SET current_track_id = ?, accumulated_seconds = 0, started_at = ?, updated_at = datetime('now')
                WHERE playlist_id = ?
                """,
                (track_id, new_started_at, playlist_id),
            )
            connection.commit()

        return self.get_playback_state(playlist_id)

    def set_playing(self, playlist_id: int, is_playing: bool) -> dict[str, object]:
        with self._connect() as connection:
            session = self._get_or_create_playback_session_row(connection, playlist_id)
            current_track_id = session["current_track_id"]
            if current_track_id is None:
                track_ids = self._list_playlist_track_ids(connection, playlist_id)
                current_track_id = track_ids[0] if track_ids else None

            currently_playing = bool(session["is_playing"])
            accumulated = float(session["accumulated_seconds"] or 0.0)
            started_at = session["started_at"]

            if currently_playing and not is_playing:
                if started_at is not None:
                    accumulated += max(0.0, time.time() - float(started_at))
                started_at = None
            elif not currently_playing and is_playing:
                started_at = time.time()

            connection.execute(
                """
                UPDATE playback_sessions
                SET current_track_id = ?, is_playing = ?, accumulated_seconds = ?, started_at = ?, updated_at = datetime('now')
                WHERE playlist_id = ?
                """,
                (current_track_id, 1 if is_playing else 0, accumulated, started_at, playlist_id),
            )
            connection.commit()

        return self.get_playback_state(playlist_id)

    def seek(self, playlist_id: int, seconds: float) -> dict[str, object]:
        if seconds < 0:
            raise ValueError("Seek position must be >= 0")

        with self._connect() as connection:
            session = self._get_or_create_playback_session_row(connection, playlist_id)
            started_at = time.time() if bool(session["is_playing"]) else None
            connection.execute(
                """
                UPDATE playback_sessions
                SET accumulated_seconds = ?, started_at = ?, updated_at = datetime('now')
                WHERE playlist_id = ?
                """,
                (seconds, started_at, playlist_id),
            )
            connection.commit()

        return self.get_playback_state(playlist_id)

    def move_track(self, playlist_id: int, direction: str) -> dict[str, object]:
        if direction not in {"next", "previous"}:
            raise ValueError("Direction must be 'next' or 'previous'")

        with self._connect() as connection:
            session = self._get_or_create_playback_session_row(connection, playlist_id)
            track_ids = self._list_playlist_track_ids(connection, playlist_id)
            if not track_ids:
                raise ValueError(f"Playlist '{playlist_id}' has no tracks")

            current_track_id = session["current_track_id"]
            if current_track_id in track_ids:
                index = track_ids.index(current_track_id)
            else:
                index = 0

            if direction == "next":
                new_index = (index + 1) % len(track_ids)
            else:
                new_index = (index - 1) % len(track_ids)

            new_track_id = track_ids[new_index]
            new_started_at = time.time() if bool(session["is_playing"]) else None

            connection.execute(
                """
                UPDATE playback_sessions
                SET current_track_id = ?, accumulated_seconds = 0, started_at = ?, updated_at = datetime('now')
                WHERE playlist_id = ?
                """,
                (new_track_id, new_started_at, playlist_id),
            )
            connection.commit()

        return self.get_playback_state(playlist_id)


_library_repository: LibraryRepository | None = None


def get_library_repository() -> LibraryRepository:
    global _library_repository
    if _library_repository is None:
        _library_repository = LibraryRepository()
    return _library_repository
