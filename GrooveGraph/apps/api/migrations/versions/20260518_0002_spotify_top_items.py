"""spotify top items

Revision ID: 20260518_0002
Revises: 20260518_0001
Create Date: 2026-05-18
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260518_0002"
down_revision: Union[str, None] = "20260518_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

uuid_type = postgresql.UUID(as_uuid=True)


def timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "user_top_tracks",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("user_id", uuid_type, nullable=False),
        sa.Column("track_id", uuid_type, nullable=False),
        sa.Column("time_range", sa.String(length=32), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=False),
        *timestamps(),
        sa.ForeignKeyConstraint(["track_id"], ["spotify_tracks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "track_id", "time_range", name="uq_user_top_track_range"),
    )
    op.create_index("ix_user_top_tracks_time_range", "user_top_tracks", ["time_range"])
    op.create_index("ix_user_top_tracks_user_id", "user_top_tracks", ["user_id"])

    op.create_table(
        "user_top_artists",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("user_id", uuid_type, nullable=False),
        sa.Column("artist_id", uuid_type, nullable=False),
        sa.Column("time_range", sa.String(length=32), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=False),
        *timestamps(),
        sa.ForeignKeyConstraint(["artist_id"], ["spotify_artists.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "artist_id", "time_range", name="uq_user_top_artist_range"),
    )
    op.create_index("ix_user_top_artists_time_range", "user_top_artists", ["time_range"])
    op.create_index("ix_user_top_artists_user_id", "user_top_artists", ["user_id"])


def downgrade() -> None:
    op.drop_table("user_top_artists")
    op.drop_table("user_top_tracks")
