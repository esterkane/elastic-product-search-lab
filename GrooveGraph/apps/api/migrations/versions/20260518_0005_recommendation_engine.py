"""recommendation engine feedback

Revision ID: 20260518_0005
Revises: 20260518_0004
Create Date: 2026-05-18
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260518_0005"
down_revision: Union[str, None] = "20260518_0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

uuid_type = postgresql.UUID(as_uuid=True)


def timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    ]


def upgrade() -> None:
    op.add_column("recommendation_candidates", sa.Column("candidate_key", sa.String(length=300), nullable=True))
    op.add_column("recommendation_candidates", sa.Column("candidate_type", sa.String(length=32), nullable=True))
    op.create_index(
        "ix_recommendation_candidates_candidate_key",
        "recommendation_candidates",
        ["candidate_key"],
    )
    op.create_index(
        "ix_recommendation_candidates_candidate_type",
        "recommendation_candidates",
        ["candidate_type"],
    )

    op.create_table(
        "recommendation_feedback",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("user_id", uuid_type, nullable=False),
        sa.Column("candidate_id", uuid_type, nullable=True),
        sa.Column("candidate_key", sa.String(length=300), nullable=False),
        sa.Column("action", sa.String(length=32), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        *timestamps(),
        sa.ForeignKeyConstraint(["candidate_id"], ["recommendation_candidates.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "candidate_key", name="uq_recommendation_feedback_user_candidate"),
    )
    op.create_index("ix_recommendation_feedback_user_id", "recommendation_feedback", ["user_id"])
    op.create_index("ix_recommendation_feedback_candidate_key", "recommendation_feedback", ["candidate_key"])


def downgrade() -> None:
    op.drop_table("recommendation_feedback")
    op.drop_index("ix_recommendation_candidates_candidate_type", table_name="recommendation_candidates")
    op.drop_index("ix_recommendation_candidates_candidate_key", table_name="recommendation_candidates")
    op.drop_column("recommendation_candidates", "candidate_type")
    op.drop_column("recommendation_candidates", "candidate_key")
