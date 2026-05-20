"""live events

Revision ID: 20260518_0004
Revises: 20260518_0003
Create Date: 2026-05-18
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260518_0004"
down_revision: Union[str, None] = "20260518_0003"
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
        "venues",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("source_id", sa.String(length=200), nullable=True),
        sa.Column("name", sa.String(length=300), nullable=False),
        sa.Column("city", sa.String(length=160), nullable=True),
        sa.Column("region", sa.String(length=160), nullable=True),
        sa.Column("country", sa.String(length=80), nullable=True),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("url", sa.Text(), nullable=True),
        *timestamps(),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_venues_city", "venues", ["city"])
    op.create_index("ix_venues_country", "venues", ["country"])
    op.create_index("ix_venues_city_country", "venues", ["city", "country"])
    op.create_index("ix_venues_source_id", "venues", ["source_id"])

    op.create_table(
        "events",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("source_id", sa.String(length=200), nullable=False),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("venue_id", uuid_type, nullable=True),
        sa.Column("city", sa.String(length=160), nullable=True),
        sa.Column("region", sa.String(length=160), nullable=True),
        sa.Column("country", sa.String(length=80), nullable=True),
        sa.Column("ticket_url", sa.Text(), nullable=True),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("lineup", json_type, nullable=False),
        sa.Column("metadata", json_type, nullable=False),
        sa.Column("is_current", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("confidence", sa.Float(), nullable=False, server_default=sa.text("0.7")),
        *timestamps(),
        sa.ForeignKeyConstraint(["venue_id"], ["venues.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_id"),
    )
    op.create_index("ix_events_city", "events", ["city"])
    op.create_index("ix_events_country", "events", ["country"])
    op.create_index("ix_events_city_country", "events", ["city", "country"])
    op.create_index("ix_events_source_id", "events", ["source_id"])
    op.create_index("ix_events_starts_at", "events", ["starts_at"])
    op.create_index("ix_events_venue_id", "events", ["venue_id"])

    op.create_table(
        "artist_events",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("artist_id", uuid_type, nullable=False),
        sa.Column("event_id", uuid_type, nullable=False),
        sa.Column("source_id", sa.String(length=200), nullable=False),
        sa.Column("role", sa.String(length=80), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=False, server_default=sa.text("0.7")),
        *timestamps(),
        sa.ForeignKeyConstraint(["artist_id"], ["spotify_artists.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("artist_id", "event_id", name="uq_artist_event"),
    )
    op.create_index("ix_artist_events_artist_id", "artist_events", ["artist_id"])
    op.create_index("ix_artist_events_event_id", "artist_events", ["event_id"])
    op.create_index("ix_artist_events_source_id", "artist_events", ["source_id"])


def downgrade() -> None:
    op.drop_table("artist_events")
    op.drop_table("events")
    op.drop_table("venues")
