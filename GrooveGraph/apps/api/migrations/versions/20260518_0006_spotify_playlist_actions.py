"""spotify playlist actions

Revision ID: 20260518_0006
Revises: 20260518_0005
Create Date: 2026-05-18
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260518_0006"
down_revision: Union[str, None] = "20260518_0005"
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
        "spotify_playlist_actions",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("user_id", uuid_type, nullable=False),
        sa.Column("playlist_id", uuid_type, nullable=True),
        sa.Column("spotify_playlist_id", sa.String(length=128), nullable=True),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("request_metadata", json_type, nullable=False),
        sa.Column("result_metadata", json_type, nullable=False),
        sa.Column("source_snapshot", json_type, nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        *timestamps(),
        sa.ForeignKeyConstraint(["playlist_id"], ["spotify_playlists.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_spotify_playlist_actions_user_id", "spotify_playlist_actions", ["user_id"])
    op.create_index(
        "ix_spotify_playlist_actions_spotify_playlist_id",
        "spotify_playlist_actions",
        ["spotify_playlist_id"],
    )


def downgrade() -> None:
    op.drop_table("spotify_playlist_actions")
