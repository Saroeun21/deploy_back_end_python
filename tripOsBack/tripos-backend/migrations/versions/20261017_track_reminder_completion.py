"""Track when reminders are completed.

Revision ID: 20261017_reminder_completed_at
Revises: 20261017_track_ai_human_review
Create Date: 2026-10-17
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20261017_reminder_completed_at"
down_revision: Union[str, None] = "20261017_track_ai_human_review"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "reminders",
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("reminders", "completed_at")
