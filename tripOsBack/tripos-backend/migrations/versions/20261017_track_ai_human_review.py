"""Track whether AI extractions need human review.

Revision ID: 20261017_track_ai_human_review
Revises: 20261017_delete_user_cascade
Create Date: 2026-10-17
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20261017_track_ai_human_review"
down_revision: Union[str, None] = "20261017_delete_user_cascade"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "ai_extractions",
        sa.Column(
            "requires_human_review",
            sa.Boolean(),
            server_default=sa.false(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("ai_extractions", "requires_human_review")
