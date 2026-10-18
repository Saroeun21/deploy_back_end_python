"""Track scheduled reminder email delivery.

Revision ID: 20261016_reminder_email_delivery
Revises: 20261016_google_avatar_url
Create Date: 2026-10-16
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20261016_reminder_email_delivery"
down_revision: Union[str, None] = "20261016_google_avatar_url"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "reminders",
        sa.Column("email_sent_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "reminders",
        sa.Column("email_claimed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_reminders_email_claimed_at",
        "reminders",
        ["email_claimed_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_reminders_email_claimed_at", table_name="reminders")
    op.drop_column("reminders", "email_claimed_at")
    op.drop_column("reminders", "email_sent_at")
