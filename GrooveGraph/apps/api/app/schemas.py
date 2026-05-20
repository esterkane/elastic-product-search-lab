import uuid
from datetime import datetime
from typing import Any

from pydantic import AliasChoices, BaseModel, ConfigDict, Field


class TimestampedSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime | None = None
    updated_at: datetime | None = None


class Track(TimestampedSchema):
    spotify_id: str
    name: str
    album_name: str | None = None
    duration_ms: int | None = None
    preview_url: str | None = None
    external_url: str | None = None


class Artist(TimestampedSchema):
    spotify_id: str
    name: str
    genres: dict[str, Any] = Field(default_factory=dict)
    external_url: str | None = None


class Playlist(TimestampedSchema):
    spotify_id: str
    owner_spotify_id: str | None = None
    name: str
    description: str | None = None
    external_url: str | None = None


class RecommendationCandidate(TimestampedSchema):
    run_id: uuid.UUID
    track_id: uuid.UUID | None = None
    artist_id: uuid.UUID | None = None
    score: float
    reason: str | None = None
    evidence: dict[str, Any] = Field(default_factory=dict)


class SourceDocument(TimestampedSchema):
    source_id: str
    title: str
    url: str | None = None
    source_type: str
    metadata: dict[str, Any] = Field(default_factory=dict, validation_alias=AliasChoices("metadata", "source_metadata"))


class SessionMessage(TimestampedSchema):
    session_id: uuid.UUID
    role: str
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict, validation_alias=AliasChoices("metadata", "message_metadata"))


class Venue(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID | None = None
    name: str
    city: str | None = None
    region: str | None = None
    country: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    url: str | None = None


class ConcertEvent(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    source_id: str
    source: str
    title: str
    starts_at: datetime | None = None
    venue: Venue | None = None
    city: str | None = None
    country: str | None = None
    ticket_url: str | None = None
    source_url: str | None = None
    lineup: list[str] = Field(default_factory=list)
    confidence: float = 0.7
    source_status: str = "current"
    artist_id: str | None = None
    artist_name: str | None = None
