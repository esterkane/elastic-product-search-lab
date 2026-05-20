"""agent checkpoints

Revision ID: 20260518_0003
Revises: 20260518_0002
Create Date: 2026-05-18
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260518_0003"
down_revision: Union[str, None] = "20260518_0002"
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
        "agent_checkpoints",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("session_id", uuid_type, nullable=False),
        sa.Column("user_id", uuid_type, nullable=False),
        sa.Column("external_session_id", sa.String(length=200), nullable=False),
        sa.Column("state", json_type, nullable=False),
        *timestamps(),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("session_id", name="uq_agent_checkpoints_session_id"),
    )
    op.create_index("ix_agent_checkpoints_external_session_id", "agent_checkpoints", ["external_session_id"])
    op.create_index("ix_agent_checkpoints_session_id", "agent_checkpoints", ["session_id"])
    op.create_index("ix_agent_checkpoints_user_id", "agent_checkpoints", ["user_id"])


def downgrade() -> None:
    op.drop_table("agent_checkpoints")
