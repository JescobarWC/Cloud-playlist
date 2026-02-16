from __future__ import annotations

import json
import time
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from app.infrastructure.postgres_models import metadata


class PostgresLibraryRepository:
    def __init__(self, database_url: str) -> None:
        self.database_url = database_url
        self.engine: Engine = create_engine(database_url)
        metadata.create_all(self.engine)

    def create_playlist(self, name: str) -> int:
        with self.engine.begin() as conn:
            playlist_id = conn.execute(text("INSERT INTO playlists (name) VALUES (:name) RETURNING id"), {"name": name}).scalar_one()
            conn.execute(
                text(
                    """
                    INSERT INTO playback_sessions (playlist_id, current_track_id, accumulated_seconds, started_at, is_playing)
                    VALUES (:playlist_id, NULL, 0, NULL, false)
                    ON CONFLICT (playlist_id) DO NOTHING
                    """
                ),
                {"playlist_id": playlist_id},
            )
            return int(playlist_id)

    def add_track_to_playlist(self, playlist_id: int, title: str, artist: str, file_path: str) -> int:
        with self.engine.begin() as conn:
            exists = conn.execute(text("SELECT id FROM playlists WHERE id = :pid"), {"pid": playlist_id}).first()
            if exists is None:
                raise ValueError(f"Playlist '{playlist_id}' not found")

            track_id = conn.execute(
                text("INSERT INTO tracks (title, artist, file_path) VALUES (:t, :a, :f) RETURNING id"),
                {"t": title, "a": artist, "f": file_path},
            ).scalar_one()

            next_position = conn.execute(
                text("SELECT COALESCE(MAX(position), 0) + 1 FROM playlist_tracks WHERE playlist_id = :pid"),
                {"pid": playlist_id},
            ).scalar_one()

            conn.execute(
                text("INSERT INTO playlist_tracks (playlist_id, track_id, position) VALUES (:pid, :tid, :pos)"),
                {"pid": playlist_id, "tid": track_id, "pos": int(next_position)},
            )

            current_track = conn.execute(
                text("SELECT current_track_id FROM playback_sessions WHERE playlist_id = :pid"),
                {"pid": playlist_id},
            ).first()
            if current_track is not None and current_track[0] is None:
                conn.execute(
                    text("UPDATE playback_sessions SET current_track_id = :tid, updated_at = now() WHERE playlist_id = :pid"),
                    {"tid": track_id, "pid": playlist_id},
                )

            return int(track_id)

    def get_track(self, track_id: int) -> dict[str, object] | None:
        with self.engine.begin() as conn:
            row = conn.execute(
                text("SELECT id, title, artist, file_path FROM tracks WHERE id = :tid"),
                {"tid": track_id},
            ).mappings().first()
        if row is None:
            return None
        return {"id": int(row["id"]), "title": row["title"], "artist": row["artist"], "file_path": row["file_path"]}

    def save_track_analysis(self, track_id: int, bpm: float | None, musical_key: str | None, waveform_json: str) -> None:
        with self.engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO track_analysis (track_id, bpm, musical_key, waveform_json)
                    VALUES (:tid, :bpm, :key, :wave)
                    ON CONFLICT (track_id) DO UPDATE SET
                      bpm = EXCLUDED.bpm,
                      musical_key = EXCLUDED.musical_key,
                      waveform_json = EXCLUDED.waveform_json,
                      analyzed_at = now()
                    """
                ),
                {"tid": track_id, "bpm": bpm, "key": musical_key, "wave": waveform_json},
            )

    def get_playlist(self, playlist_id: int) -> dict[str, object] | None:
        with self.engine.begin() as conn:
            playlist = conn.execute(text("SELECT id, name FROM playlists WHERE id = :pid"), {"pid": playlist_id}).mappings().first()
            if playlist is None:
                return None
            tracks = conn.execute(
                text(
                    """
                    SELECT t.id, t.title, t.artist, t.file_path, pt.position, ta.bpm, ta.musical_key, ta.waveform_json
                    FROM playlist_tracks pt
                    JOIN tracks t ON t.id = pt.track_id
                    LEFT JOIN track_analysis ta ON ta.track_id = t.id
                    WHERE pt.playlist_id = :pid
                    ORDER BY pt.position ASC
                    """
                ),
                {"pid": playlist_id},
            ).mappings().all()

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
        with self.engine.begin() as conn:
            exists = conn.execute(text("SELECT id FROM playlists WHERE id = :pid"), {"pid": playlist_id}).first()
            if exists is None:
                raise ValueError(f"Playlist '{playlist_id}' not found")
            rows = conn.execute(
                text(
                    """
                    SELECT t.id, t.file_path
                    FROM playlist_tracks pt
                    JOIN tracks t ON t.id = pt.track_id
                    WHERE pt.playlist_id = :pid
                    ORDER BY pt.position ASC
                    """
                ),
                {"pid": playlist_id},
            ).mappings().all()
        return [{"track_id": int(r["id"]), "file_path": r["file_path"]} for r in rows]

    def create_analysis_job(self, job_id: str, playlist_id: int, total_tracks: int) -> None:
        with self.engine.begin() as conn:
            exists = conn.execute(text("SELECT id FROM playlists WHERE id = :pid"), {"pid": playlist_id}).first()
            if exists is None:
                raise ValueError(f"Playlist '{playlist_id}' not found")
            conn.execute(
                text(
                    """
                    INSERT INTO analysis_jobs (id, playlist_id, status, total_tracks, analyzed_tracks, failed_tracks)
                    VALUES (:jid, :pid, 'queued', :total, 0, 0)
                    """
                ),
                {"jid": job_id, "pid": playlist_id, "total": total_tracks},
            )

    def start_analysis_job(self, job_id: str) -> None:
        with self.engine.begin() as conn:
            conn.execute(
                text("UPDATE analysis_jobs SET status='running', error_message=NULL, cancelled_at=NULL, updated_at=now() WHERE id=:jid"),
                {"jid": job_id},
            )

    def record_analysis_job_progress(self, job_id: str, analyzed_increment: int = 0, failed_increment: int = 0) -> None:
        with self.engine.begin() as conn:
            conn.execute(
                text(
                    """
                    UPDATE analysis_jobs
                    SET analyzed_tracks = analyzed_tracks + :a,
                        failed_tracks = failed_tracks + :f,
                        updated_at = now()
                    WHERE id = :jid
                    """
                ),
                {"a": analyzed_increment, "f": failed_increment, "jid": job_id},
            )

    def complete_analysis_job(self, job_id: str) -> None:
        with self.engine.begin() as conn:
            row = conn.execute(text("SELECT failed_tracks, status FROM analysis_jobs WHERE id=:jid"), {"jid": job_id}).mappings().first()
            if row is None:
                raise ValueError(f"Analysis job '{job_id}' not found")
            if row["status"] == "cancelled":
                return
            status = "completed_with_errors" if int(row["failed_tracks"]) > 0 else "completed"
            conn.execute(text("UPDATE analysis_jobs SET status=:status, updated_at=now() WHERE id=:jid"), {"status": status, "jid": job_id})

    def fail_analysis_job(self, job_id: str, error_message: str) -> None:
        with self.engine.begin() as conn:
            conn.execute(
                text("UPDATE analysis_jobs SET status='failed', error_message=:msg, updated_at=now() WHERE id=:jid"),
                {"msg": error_message, "jid": job_id},
            )

    def cancel_analysis_job(self, job_id: str) -> dict[str, object]:
        with self.engine.begin() as conn:
            row = conn.execute(text("SELECT status FROM analysis_jobs WHERE id=:jid"), {"jid": job_id}).mappings().first()
            if row is None:
                raise ValueError(f"Analysis job '{job_id}' not found")
            status = row["status"]
            if status in {"completed", "completed_with_errors", "failed", "cancelled"}:
                return {"job_id": job_id, "status": status}
            conn.execute(text("UPDATE analysis_jobs SET status='cancelled', cancelled_at=now(), updated_at=now() WHERE id=:jid"), {"jid": job_id})
            return {"job_id": job_id, "status": "cancelled"}

    def is_analysis_job_cancelled(self, job_id: str) -> bool:
        with self.engine.begin() as conn:
            row = conn.execute(text("SELECT status FROM analysis_jobs WHERE id=:jid"), {"jid": job_id}).mappings().first()
        if row is None:
            raise ValueError(f"Analysis job '{job_id}' not found")
        return row["status"] == "cancelled"

    def get_analysis_job(self, job_id: str) -> dict[str, object] | None:
        with self.engine.begin() as conn:
            row = conn.execute(
                text(
                    """
                    SELECT id, playlist_id, status, total_tracks, analyzed_tracks, failed_tracks, error_message, cancelled_at, created_at, updated_at
                    FROM analysis_jobs WHERE id = :jid
                    """
                ),
                {"jid": job_id},
            ).mappings().first()
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
            "cancelled_at": row["cancelled_at"].isoformat() if row["cancelled_at"] else None,
            "created_at": row["created_at"].isoformat(),
            "updated_at": row["updated_at"].isoformat(),
        }

    def _list_playlist_track_ids(self, playlist_id: int) -> list[int]:
        with self.engine.begin() as conn:
            rows = conn.execute(
                text("SELECT track_id FROM playlist_tracks WHERE playlist_id=:pid ORDER BY position ASC"),
                {"pid": playlist_id},
            ).all()
        return [int(r[0]) for r in rows]

    def _playback_state_row(self, playlist_id: int):
        with self.engine.begin() as conn:
            exists = conn.execute(text("SELECT id FROM playlists WHERE id=:pid"), {"pid": playlist_id}).first()
            if exists is None:
                raise ValueError(f"Playlist '{playlist_id}' not found")
            conn.execute(
                text(
                    """
                    INSERT INTO playback_sessions (playlist_id, current_track_id, accumulated_seconds, started_at, is_playing)
                    VALUES (:pid, NULL, 0, NULL, false)
                    ON CONFLICT (playlist_id) DO NOTHING
                    """
                ),
                {"pid": playlist_id},
            )
            row = conn.execute(
                text("SELECT current_track_id, accumulated_seconds, started_at, is_playing FROM playback_sessions WHERE playlist_id=:pid"),
                {"pid": playlist_id},
            ).mappings().first()
        return row

    def _compute_position_seconds(self, session: dict) -> float:
        accumulated = float(session["accumulated_seconds"] or 0.0)
        if not bool(session["is_playing"]):
            return accumulated
        started_at = session["started_at"]
        if started_at is None:
            return accumulated
        return accumulated + max(0.0, time.time() - float(started_at))

    def get_playback_state(self, playlist_id: int) -> dict[str, object]:
        session = self._playback_state_row(playlist_id)
        track_ids = self._list_playlist_track_ids(playlist_id)
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
        track_ids = self._list_playlist_track_ids(playlist_id)
        if track_id not in track_ids:
            raise ValueError(f"Track '{track_id}' is not in playlist '{playlist_id}'")
        session = self._playback_state_row(playlist_id)
        new_started_at = time.time() if bool(session["is_playing"]) else None
        with self.engine.begin() as conn:
            conn.execute(
                text("UPDATE playback_sessions SET current_track_id=:tid, accumulated_seconds=0, started_at=:st, updated_at=now() WHERE playlist_id=:pid"),
                {"tid": track_id, "st": new_started_at, "pid": playlist_id},
            )
        return self.get_playback_state(playlist_id)

    def set_playing(self, playlist_id: int, is_playing: bool) -> dict[str, object]:
        session = self._playback_state_row(playlist_id)
        current_track_id = session["current_track_id"]
        if current_track_id is None:
            ids = self._list_playlist_track_ids(playlist_id)
            current_track_id = ids[0] if ids else None

        currently_playing = bool(session["is_playing"])
        accumulated = float(session["accumulated_seconds"] or 0.0)
        started_at = session["started_at"]
        if currently_playing and not is_playing and started_at is not None:
            accumulated += max(0.0, time.time() - float(started_at))
            started_at = None
        elif not currently_playing and is_playing:
            started_at = time.time()

        with self.engine.begin() as conn:
            conn.execute(
                text("UPDATE playback_sessions SET current_track_id=:tid, is_playing=:p, accumulated_seconds=:acc, started_at=:st, updated_at=now() WHERE playlist_id=:pid"),
                {"tid": current_track_id, "p": bool(is_playing), "acc": accumulated, "st": started_at, "pid": playlist_id},
            )
        return self.get_playback_state(playlist_id)

    def seek(self, playlist_id: int, seconds: float) -> dict[str, object]:
        if seconds < 0:
            raise ValueError("Seek position must be >= 0")
        session = self._playback_state_row(playlist_id)
        started_at = time.time() if bool(session["is_playing"]) else None
        with self.engine.begin() as conn:
            conn.execute(
                text("UPDATE playback_sessions SET accumulated_seconds=:s, started_at=:st, updated_at=now() WHERE playlist_id=:pid"),
                {"s": seconds, "st": started_at, "pid": playlist_id},
            )
        return self.get_playback_state(playlist_id)

    def move_track(self, playlist_id: int, direction: str) -> dict[str, object]:
        if direction not in {"next", "previous"}:
            raise ValueError("Direction must be 'next' or 'previous'")
        session = self._playback_state_row(playlist_id)
        track_ids = self._list_playlist_track_ids(playlist_id)
        if not track_ids:
            raise ValueError(f"Playlist '{playlist_id}' has no tracks")
        current = session["current_track_id"]
        idx = track_ids.index(current) if current in track_ids else 0
        new_idx = (idx + 1) % len(track_ids) if direction == "next" else (idx - 1) % len(track_ids)
        new_track_id = track_ids[new_idx]
        new_started_at = time.time() if bool(session["is_playing"]) else None
        with self.engine.begin() as conn:
            conn.execute(
                text("UPDATE playback_sessions SET current_track_id=:tid, accumulated_seconds=0, started_at=:st, updated_at=now() WHERE playlist_id=:pid"),
                {"tid": new_track_id, "st": new_started_at, "pid": playlist_id},
            )
        return self.get_playback_state(playlist_id)

    def find_duplicate_tracks(self) -> list[dict[str, object]]:
        with self.engine.begin() as conn:
            rows = conn.execute(
                text(
                    """
                    SELECT LOWER(title) AS normalized_title,
                           LOWER(artist) AS normalized_artist,
                           COUNT(*) AS track_count,
                           STRING_AGG(CAST(id AS TEXT), ',') AS track_ids
                    FROM tracks
                    GROUP BY normalized_title, normalized_artist
                    HAVING COUNT(*) > 1
                    ORDER BY track_count DESC, normalized_title ASC
                    """
                )
            ).mappings().all()
        duplicates = []
        for row in rows:
            ids = [int(x) for x in str(row["track_ids"]).split(",") if x]
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
        with self.engine.begin() as conn:
            rows = conn.execute(
                text(f"SELECT id, {field_name} AS old_value FROM tracks WHERE {field_name} LIKE :q"),
                {"q": f"%{search_text}%"},
            ).mappings().all()
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
        with self.engine.begin() as conn:
            conn.execute(
                text("INSERT INTO replace_operations (id, field_name, search_text, replace_text) VALUES (:id, :f, :s, :r)"),
                {"id": operation_id, "f": field_name, "s": search_text, "r": replace_text},
            )
            for item in preview:
                conn.execute(
                    text(
                        "INSERT INTO replace_changes (operation_id, track_id, field_name, old_value, new_value) VALUES (:op, :tid, :f, :old, :new)"
                    ),
                    {
                        "op": operation_id,
                        "tid": item["track_id"],
                        "f": field_name,
                        "old": item["old_value"],
                        "new": item["new_value"],
                    },
                )
                conn.execute(
                    text(f"UPDATE tracks SET {field_name} = :new WHERE id = :tid"),
                    {"new": item["new_value"], "tid": item["track_id"]},
                )
        return {"operation_id": operation_id, "changed_tracks": len(preview)}

    def undo_find_replace(self, operation_id: str) -> dict[str, object]:
        with self.engine.begin() as conn:
            rows = conn.execute(
                text("SELECT track_id, field_name, old_value FROM replace_changes WHERE operation_id = :op"),
                {"op": operation_id},
            ).mappings().all()
            if not rows:
                raise ValueError(f"Replace operation '{operation_id}' not found")
            for row in rows:
                f = row["field_name"]
                if f not in {"title", "artist"}:
                    continue
                conn.execute(text(f"UPDATE tracks SET {f} = :old WHERE id = :tid"), {"old": row["old_value"], "tid": int(row["track_id"])})
            conn.execute(text("DELETE FROM replace_changes WHERE operation_id=:op"), {"op": operation_id})
            conn.execute(text("DELETE FROM replace_operations WHERE id=:op"), {"op": operation_id})
        return {"operation_id": operation_id, "restored_tracks": len(rows)}
