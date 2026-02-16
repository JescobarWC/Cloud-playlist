from __future__ import annotations

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    func,
)

metadata = MetaData()

playlists_table = Table(
    "playlists",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("name", String(255), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
)

tracks_table = Table(
    "tracks",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("title", String(1024), nullable=False),
    Column("artist", String(1024), nullable=False),
    Column("file_path", String(4096), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
)

playlist_tracks_table = Table(
    "playlist_tracks",
    metadata,
    Column("playlist_id", Integer, ForeignKey("playlists.id", ondelete="CASCADE"), primary_key=True),
    Column("track_id", Integer, ForeignKey("tracks.id", ondelete="CASCADE"), primary_key=True),
    Column("position", Integer, nullable=False),
)

track_analysis_table = Table(
    "track_analysis",
    metadata,
    Column("track_id", Integer, ForeignKey("tracks.id", ondelete="CASCADE"), primary_key=True),
    Column("bpm", Float),
    Column("musical_key", String(32)),
    Column("waveform_json", Text, nullable=False),
    Column("analyzed_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
)

playback_sessions_table = Table(
    "playback_sessions",
    metadata,
    Column("playlist_id", Integer, ForeignKey("playlists.id", ondelete="CASCADE"), primary_key=True),
    Column("current_track_id", Integer, ForeignKey("tracks.id", ondelete="SET NULL")),
    Column("accumulated_seconds", Float, nullable=False, server_default="0"),
    Column("started_at", Float),
    Column("is_playing", Boolean, nullable=False, server_default="false"),
    Column("updated_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
)

analysis_jobs_table = Table(
    "analysis_jobs",
    metadata,
    Column("id", String(64), primary_key=True),
    Column("playlist_id", Integer, ForeignKey("playlists.id", ondelete="CASCADE"), nullable=False),
    Column("status", String(64), nullable=False),
    Column("total_tracks", Integer, nullable=False, server_default="0"),
    Column("analyzed_tracks", Integer, nullable=False, server_default="0"),
    Column("failed_tracks", Integer, nullable=False, server_default="0"),
    Column("error_message", Text),
    Column("cancelled_at", DateTime(timezone=True)),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("updated_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
)

replace_operations_table = Table(
    "replace_operations",
    metadata,
    Column("id", String(64), primary_key=True),
    Column("field_name", String(64), nullable=False),
    Column("search_text", Text, nullable=False),
    Column("replace_text", Text, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
)

replace_changes_table = Table(
    "replace_changes",
    metadata,
    Column("operation_id", String(64), ForeignKey("replace_operations.id", ondelete="CASCADE"), primary_key=True),
    Column("track_id", Integer, ForeignKey("tracks.id", ondelete="CASCADE"), primary_key=True),
    Column("field_name", String(64), primary_key=True),
    Column("old_value", Text, nullable=False),
    Column("new_value", Text, nullable=False),
)

import_jobs_table = Table(
    "import_jobs",
    metadata,
    Column("id", String(64), primary_key=True),
    Column("connector", String(32), nullable=False),
    Column("source_uri", String(2048), nullable=False),
    Column("status", String(32), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
)
