"""initial domain models

Revision ID: 20260518_0001
Revises:
Create Date: 2026-05-18
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260518_0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

uuid_type = postgresql.UUID(as_uuid=True)
json_type = postgresql.JSONB(astext_type=sa.Text())


def timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("display_name", sa.String(length=200), nullable=True),
        sa.Column("locale", sa.String(length=32), nullable=True),
        *timestamps(),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "spotify_artists",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("spotify_id", sa.String(length=128), nullable=False),
        sa.Column("name", sa.String(length=300), nullable=False),
        sa.Column("genres", json_type, nullable=False),
        sa.Column("external_url", sa.Text(), nullable=True),
        *timestamps(),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_spotify_artists_spotify_id", "spotify_artists", ["spotify_id"], unique=True)

    op.create_table(
        "spotify_tracks",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("spotify_id", sa.String(length=128), nullable=False),
        sa.Column("name", sa.String(length=300), nullable=False),
        sa.Column("album_name", sa.String(length=300), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("preview_url", sa.Text(), nullable=True),
        sa.Column("external_url", sa.Text(), nullable=True),
        *timestamps(),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_spotify_tracks_spotify_id", "spotify_tracks", ["spotify_id"], unique=True)

    op.create_table(
        "spotify_playlists",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("spotify_id", sa.String(length=128), nullable=False),
        sa.Column("owner_spotify_id", sa.String(length=128), nullable=True),
        sa.Column("name", sa.String(length=300), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("external_url", sa.Text(), nullable=True),
        *timestamps(),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_spotify_playlists_owner_spotify_id", "spotify_playlists", ["owner_spotify_id"])
    op.create_index("ix_spotify_playlists_spotify_id", "spotify_playlists", ["spotify_id"], unique=True)

    op.create_table(
        "source_documents",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("source_id", sa.String(length=200), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("url", sa.Text(), nullable=True),
        sa.Column("source_type", sa.String(length=64), nullable=False),
        sa.Column("metadata", json_type, nullable=False),
        *timestamps(),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_source_documents_source_id", "source_documents", ["source_id"], unique=True)

    op.create_table(
        "eval_runs",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("dataset", sa.String(length=200), nullable=True),
        sa.Column("metrics", json_type, nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        *timestamps(),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "oauth_accounts",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("user_id", uuid_type, nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("provider_account_id", sa.String(length=128), nullable=False),
        sa.Column("encrypted_access_token", sa.Text(), nullable=True),
        sa.Column("encrypted_refresh_token", sa.Text(), nullable=True),
        sa.Column("scopes", sa.Text(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        *timestamps(),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider", "provider_account_id", name="uq_oauth_provider_account"),
    )
    op.create_index("ix_oauth_accounts_user_id", "oauth_accounts", ["user_id"])

    op.create_table(
        "sessions",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("user_id", uuid_type, nullable=False),
        sa.Column("title", sa.String(length=200), nullable=True),
        *timestamps(),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sessions_user_id", "sessions", ["user_id"])

    op.create_table(
        "source_chunks",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("source_id", uuid_type, nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("embedding_id", sa.String(length=200), nullable=True),
        *timestamps(),
        sa.ForeignKeyConstraint(["source_id"], ["source_documents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_source_chunks_source_id", "source_chunks", ["source_id"])
    op.create_index("ix_source_chunks_source_id_position", "source_chunks", ["source_id", "position"])

    op.create_table(
        "user_followed_artists",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("user_id", uuid_type, nullable=False),
        sa.Column("artist_id", uuid_type, nullable=False),
        sa.Column("followed_at", sa.DateTime(timezone=True), nullable=True),
        *timestamps(),
        sa.ForeignKeyConstraint(["artist_id"], ["spotify_artists.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "artist_id", name="uq_user_followed_artist"),
    )
    op.create_index("ix_user_followed_artists_user_id", "user_followed_artists", ["user_id"])

    op.create_table(
        "user_saved_tracks",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("user_id", uuid_type, nullable=False),
        sa.Column("track_id", uuid_type, nullable=False),
        sa.Column("saved_at", sa.DateTime(timezone=True), nullable=True),
        *timestamps(),
        sa.ForeignKeyConstraint(["track_id"], ["spotify_tracks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "track_id", name="uq_user_saved_track"),
    )
    op.create_index("ix_user_saved_tracks_user_id", "user_saved_tracks", ["user_id"])

    op.create_table(
        "user_playlist_tracks",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("user_id", uuid_type, nullable=False),
        sa.Column("playlist_id", uuid_type, nullable=False),
        sa.Column("track_id", uuid_type, nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        *timestamps(),
        sa.ForeignKeyConstraint(["playlist_id"], ["spotify_playlists.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["track_id"], ["spotify_tracks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("playlist_id", "track_id", "position", name="uq_playlist_track_position"),
    )
    op.create_index("ix_user_playlist_tracks_playlist_id", "user_playlist_tracks", ["playlist_id"])
    op.create_index("ix_user_playlist_tracks_user_id", "user_playlist_tracks", ["user_id"])

    op.create_table(
        "session_messages",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("session_id", uuid_type, nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("metadata", json_type, nullable=False),
        *timestamps(),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_session_messages_session_id", "session_messages", ["session_id"])

    op.create_table(
        "recommendation_runs",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("user_id", uuid_type, nullable=False),
        sa.Column("session_id", uuid_type, nullable=True),
        sa.Column("prompt", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        *timestamps(),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_recommendation_runs_session_id", "recommendation_runs", ["session_id"])
    op.create_index("ix_recommendation_runs_user_id", "recommendation_runs", ["user_id"])

    op.create_table(
        "tool_calls",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("user_id", uuid_type, nullable=True),
        sa.Column("session_id", uuid_type, nullable=True),
        sa.Column("tool_name", sa.String(length=100), nullable=False),
        sa.Column("arguments", json_type, nullable=False),
        sa.Column("result_summary", sa.Text(), nullable=True),
        *timestamps(),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_tool_calls_session_id", "tool_calls", ["session_id"])
    op.create_index("ix_tool_calls_user_id", "tool_calls", ["user_id"])

    op.create_table(
        "recommendation_candidates",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("run_id", uuid_type, nullable=False),
        sa.Column("track_id", uuid_type, nullable=True),
        sa.Column("artist_id", uuid_type, nullable=True),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("evidence", json_type, nullable=False),
        *timestamps(),
        sa.ForeignKeyConstraint(["artist_id"], ["spotify_artists.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["run_id"], ["recommendation_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["track_id"], ["spotify_tracks.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_recommendation_candidates_run_id", "recommendation_candidates", ["run_id"])


def downgrade() -> None:
    op.drop_table("recommendation_candidates")
    op.drop_table("tool_calls")
    op.drop_table("recommendation_runs")
    op.drop_table("session_messages")
    op.drop_table("user_playlist_tracks")
    op.drop_table("user_saved_tracks")
    op.drop_table("user_followed_artists")
    op.drop_table("source_chunks")
    op.drop_table("sessions")
    op.drop_table("oauth_accounts")
    op.drop_table("eval_runs")
    op.drop_table("source_documents")
    op.drop_table("spotify_playlists")
    op.drop_table("spotify_tracks")
    op.drop_table("spotify_artists")
    op.drop_table("users")
