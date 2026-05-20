import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.types import JSON


class Base(DeclarativeBase):
    type_annotation_map = {dict[str, Any]: JSON().with_variant(JSONB, "postgresql")}


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(200))
    locale: Mapped[str | None] = mapped_column(String(32))

    oauth_accounts: Mapped[list["OAuthAccount"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    sessions: Mapped[list["Session"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class OAuthAccount(Base, TimestampMixin):
    __tablename__ = "oauth_accounts"
    __table_args__ = (
        UniqueConstraint("provider", "provider_account_id", name="uq_oauth_provider_account"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    provider_account_id: Mapped[str] = mapped_column(String(128), nullable=False)
    encrypted_access_token: Mapped[str | None] = mapped_column(Text)
    encrypted_refresh_token: Mapped[str | None] = mapped_column(Text)
    scopes: Mapped[str | None] = mapped_column(Text)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped[User] = relationship(back_populates="oauth_accounts")


class Session(Base, TimestampMixin):
    __tablename__ = "sessions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    title: Mapped[str | None] = mapped_column(String(200))

    user: Mapped[User] = relationship(back_populates="sessions")
    messages: Mapped[list["SessionMessage"]] = relationship(back_populates="session", cascade="all, delete-orphan")


class MessageRole(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


class SessionMessage(Base, TimestampMixin):
    __tablename__ = "session_messages"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("sessions.id", ondelete="CASCADE"), index=True, nullable=False
    )
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    message_metadata: Mapped[dict[str, Any]] = mapped_column("metadata", default=dict, nullable=False)

    session: Mapped[Session] = relationship(back_populates="messages")


class AgentCheckpoint(Base, TimestampMixin):
    __tablename__ = "agent_checkpoints"
    __table_args__ = (
        UniqueConstraint("session_id", name="uq_agent_checkpoints_session_id"),
        Index("ix_agent_checkpoints_external_session_id", "external_session_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("sessions.id", ondelete="CASCADE"), index=True, nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    external_session_id: Mapped[str] = mapped_column(String(200), nullable=False)
    state: Mapped[dict[str, Any]] = mapped_column(default=dict, nullable=False)


class SpotifyTrack(Base, TimestampMixin):
    __tablename__ = "spotify_tracks"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    spotify_id: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    album_name: Mapped[str | None] = mapped_column(String(300))
    duration_ms: Mapped[int | None]
    preview_url: Mapped[str | None] = mapped_column(Text)
    external_url: Mapped[str | None] = mapped_column(Text)


class SpotifyArtist(Base, TimestampMixin):
    __tablename__ = "spotify_artists"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    spotify_id: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    genres: Mapped[dict[str, Any]] = mapped_column(default=dict, nullable=False)
    external_url: Mapped[str | None] = mapped_column(Text)


class Venue(Base, TimestampMixin):
    __tablename__ = "venues"
    __table_args__ = (
        Index("ix_venues_city_country", "city", "country"),
        Index("ix_venues_source_id", "source_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    source_id: Mapped[str | None] = mapped_column(String(200))
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    city: Mapped[str | None] = mapped_column(String(160), index=True)
    region: Mapped[str | None] = mapped_column(String(160))
    country: Mapped[str | None] = mapped_column(String(80), index=True)
    latitude: Mapped[float | None]
    longitude: Mapped[float | None]
    url: Mapped[str | None] = mapped_column(Text)


class Event(Base, TimestampMixin):
    __tablename__ = "events"
    __table_args__ = (
        Index("ix_events_source_id", "source_id"),
        Index("ix_events_starts_at", "starts_at"),
        Index("ix_events_city_country", "city", "country"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    source_id: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    venue_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("venues.id", ondelete="SET NULL"), index=True)
    city: Mapped[str | None] = mapped_column(String(160), index=True)
    region: Mapped[str | None] = mapped_column(String(160))
    country: Mapped[str | None] = mapped_column(String(80), index=True)
    ticket_url: Mapped[str | None] = mapped_column(Text)
    source_url: Mapped[str | None] = mapped_column(Text)
    lineup: Mapped[dict[str, Any]] = mapped_column(default=dict, nullable=False)
    source_metadata: Mapped[dict[str, Any]] = mapped_column("metadata", default=dict, nullable=False)
    is_current: Mapped[bool] = mapped_column(default=True, nullable=False)
    confidence: Mapped[float] = mapped_column(default=0.7, nullable=False)

    venue: Mapped[Venue | None] = relationship()


class ArtistEvent(Base, TimestampMixin):
    __tablename__ = "artist_events"
    __table_args__ = (
        UniqueConstraint("artist_id", "event_id", name="uq_artist_event"),
        Index("ix_artist_events_artist_id", "artist_id"),
        Index("ix_artist_events_event_id", "event_id"),
        Index("ix_artist_events_source_id", "source_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    artist_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("spotify_artists.id", ondelete="CASCADE"), nullable=False)
    event_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("events.id", ondelete="CASCADE"), nullable=False)
    source_id: Mapped[str] = mapped_column(String(200), nullable=False)
    role: Mapped[str | None] = mapped_column(String(80))
    confidence: Mapped[float] = mapped_column(default=0.7, nullable=False)


class SpotifyPlaylist(Base, TimestampMixin):
    __tablename__ = "spotify_playlists"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    spotify_id: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    owner_spotify_id: Mapped[str | None] = mapped_column(String(128), index=True)
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    external_url: Mapped[str | None] = mapped_column(Text)


class UserSavedTrack(Base, TimestampMixin):
    __tablename__ = "user_saved_tracks"
    __table_args__ = (UniqueConstraint("user_id", "track_id", name="uq_user_saved_track"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    track_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("spotify_tracks.id", ondelete="CASCADE"), nullable=False)
    saved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class UserFollowedArtist(Base, TimestampMixin):
    __tablename__ = "user_followed_artists"
    __table_args__ = (UniqueConstraint("user_id", "artist_id", name="uq_user_followed_artist"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    artist_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("spotify_artists.id", ondelete="CASCADE"), nullable=False)
    followed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class UserPlaylistTrack(Base, TimestampMixin):
    __tablename__ = "user_playlist_tracks"
    __table_args__ = (UniqueConstraint("playlist_id", "track_id", "position", name="uq_playlist_track_position"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    playlist_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("spotify_playlists.id", ondelete="CASCADE"), index=True, nullable=False
    )
    track_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("spotify_tracks.id", ondelete="CASCADE"), nullable=False)
    position: Mapped[int] = mapped_column(nullable=False)


class SpotifyPlaylistAction(Base, TimestampMixin):
    __tablename__ = "spotify_playlist_actions"
    __table_args__ = (
        Index("ix_spotify_playlist_actions_user_id", "user_id"),
        Index("ix_spotify_playlist_actions_spotify_playlist_id", "spotify_playlist_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    playlist_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("spotify_playlists.id", ondelete="SET NULL"))
    spotify_playlist_id: Mapped[str | None] = mapped_column(String(128))
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    request_metadata: Mapped[dict[str, Any]] = mapped_column(default=dict, nullable=False)
    result_metadata: Mapped[dict[str, Any]] = mapped_column(default=dict, nullable=False)
    source_snapshot: Mapped[dict[str, Any]] = mapped_column(default=dict, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text)


class UserTopTrack(Base, TimestampMixin):
    __tablename__ = "user_top_tracks"
    __table_args__ = (UniqueConstraint("user_id", "track_id", "time_range", name="uq_user_top_track_range"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    track_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("spotify_tracks.id", ondelete="CASCADE"), nullable=False)
    time_range: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    rank: Mapped[int] = mapped_column(nullable=False)


class UserTopArtist(Base, TimestampMixin):
    __tablename__ = "user_top_artists"
    __table_args__ = (UniqueConstraint("user_id", "artist_id", "time_range", name="uq_user_top_artist_range"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    artist_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("spotify_artists.id", ondelete="CASCADE"), nullable=False)
    time_range: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    rank: Mapped[int] = mapped_column(nullable=False)


class RecommendationRun(Base, TimestampMixin):
    __tablename__ = "recommendation_runs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    session_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("sessions.id", ondelete="SET NULL"), index=True)
    prompt: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)


class RecommendationCandidate(Base, TimestampMixin):
    __tablename__ = "recommendation_candidates"
    __table_args__ = (
        Index("ix_recommendation_candidates_candidate_key", "candidate_key"),
        Index("ix_recommendation_candidates_candidate_type", "candidate_type"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("recommendation_runs.id", ondelete="CASCADE"), index=True)
    track_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("spotify_tracks.id", ondelete="SET NULL"))
    artist_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("spotify_artists.id", ondelete="SET NULL"))
    candidate_key: Mapped[str | None] = mapped_column(String(300))
    candidate_type: Mapped[str | None] = mapped_column(String(32))
    score: Mapped[float] = mapped_column(default=0.0, nullable=False)
    reason: Mapped[str | None] = mapped_column(Text)
    evidence: Mapped[dict[str, Any]] = mapped_column(default=dict, nullable=False)


class RecommendationFeedback(Base, TimestampMixin):
    __tablename__ = "recommendation_feedback"
    __table_args__ = (
        UniqueConstraint("user_id", "candidate_key", name="uq_recommendation_feedback_user_candidate"),
        Index("ix_recommendation_feedback_user_id", "user_id"),
        Index("ix_recommendation_feedback_candidate_key", "candidate_key"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    candidate_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("recommendation_candidates.id", ondelete="SET NULL"))
    candidate_key: Mapped[str] = mapped_column(String(300), nullable=False)
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)


class SourceDocument(Base, TimestampMixin):
    __tablename__ = "source_documents"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    source_id: Mapped[str] = mapped_column(String(200), unique=True, index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    url: Mapped[str | None] = mapped_column(Text)
    source_type: Mapped[str] = mapped_column(String(64), nullable=False)
    source_metadata: Mapped[dict[str, Any]] = mapped_column("metadata", default=dict, nullable=False)


class SourceChunk(Base, TimestampMixin):
    __tablename__ = "source_chunks"
    __table_args__ = (Index("ix_source_chunks_source_id_position", "source_id", "position"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    source_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("source_documents.id", ondelete="CASCADE"), index=True, nullable=False
    )
    position: Mapped[int] = mapped_column(nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding_id: Mapped[str | None] = mapped_column(String(200))


class ToolCall(Base, TimestampMixin):
    __tablename__ = "tool_calls"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    session_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("sessions.id", ondelete="SET NULL"), index=True)
    tool_name: Mapped[str] = mapped_column(String(100), nullable=False)
    arguments: Mapped[dict[str, Any]] = mapped_column(default=dict, nullable=False)
    result_summary: Mapped[str | None] = mapped_column(Text)


class EvalRun(Base, TimestampMixin):
    __tablename__ = "eval_runs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    dataset: Mapped[str | None] = mapped_column(String(200))
    metrics: Mapped[dict[str, Any]] = mapped_column(default=dict, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)
