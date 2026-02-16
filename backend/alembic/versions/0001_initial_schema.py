"""Initial PostgreSQL schema baseline.

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-02-16
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "playlists",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "tracks",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("title", sa.String(length=1024), nullable=False),
        sa.Column("artist", sa.String(length=1024), nullable=False),
        sa.Column("file_path", sa.String(length=4096), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "playlist_tracks",
        sa.Column("playlist_id", sa.Integer(), sa.ForeignKey("playlists.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("track_id", sa.Integer(), sa.ForeignKey("tracks.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("position", sa.Integer(), nullable=False),
    )

    op.create_table(
        "track_analysis",
        sa.Column("track_id", sa.Integer(), sa.ForeignKey("tracks.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("bpm", sa.Float()),
        sa.Column("musical_key", sa.String(length=32)),
        sa.Column("waveform_json", sa.Text(), nullable=False),
        sa.Column("analyzed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "playback_sessions",
        sa.Column("playlist_id", sa.Integer(), sa.ForeignKey("playlists.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("current_track_id", sa.Integer(), sa.ForeignKey("tracks.id", ondelete="SET NULL")),
        sa.Column("accumulated_seconds", sa.Float(), nullable=False, server_default="0"),
        sa.Column("started_at", sa.Float()),
        sa.Column("is_playing", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "analysis_jobs",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("playlist_id", sa.Integer(), sa.ForeignKey("playlists.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("total_tracks", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("analyzed_tracks", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failed_tracks", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text()),
        sa.Column("cancelled_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "replace_operations",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("field_name", sa.String(length=64), nullable=False),
        sa.Column("search_text", sa.Text(), nullable=False),
        sa.Column("replace_text", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "replace_changes",
        sa.Column("operation_id", sa.String(length=64), sa.ForeignKey("replace_operations.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("track_id", sa.Integer(), sa.ForeignKey("tracks.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("field_name", sa.String(length=64), primary_key=True),
        sa.Column("old_value", sa.Text(), nullable=False),
        sa.Column("new_value", sa.Text(), nullable=False),
    )

    op.create_table(
        "import_jobs",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("connector", sa.String(length=32), nullable=False),
        sa.Column("source_uri", sa.String(length=2048), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("import_jobs")
    op.drop_table("replace_changes")
    op.drop_table("replace_operations")
    op.drop_table("analysis_jobs")
    op.drop_table("playback_sessions")
    op.drop_table("track_analysis")
    op.drop_table("playlist_tracks")
    op.drop_table("tracks")
    op.drop_table("playlists")
