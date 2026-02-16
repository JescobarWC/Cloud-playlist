from __future__ import annotations

import sqlite3
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
                """
            )
            connection.commit()

    def create_playlist(self, name: str) -> int:
        with self._connect() as connection:
            cursor = connection.execute("INSERT INTO playlists (name) VALUES (?)", (name,))
            connection.commit()
            return int(cursor.lastrowid)

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
                        "waveform_json": track["waveform_json"],
                    }
                    if track["waveform_json"] is not None
                    else None,
                }
                for track in tracks
            ],
        }


_library_repository: LibraryRepository | None = None


def get_library_repository() -> LibraryRepository:
    global _library_repository
    if _library_repository is None:
        _library_repository = LibraryRepository()
    return _library_repository
