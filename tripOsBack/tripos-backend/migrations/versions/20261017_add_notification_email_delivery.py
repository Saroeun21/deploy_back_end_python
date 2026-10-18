"""Add scheduled email delivery for notifications.

Revision ID: 20261017_notification_email_delivery
Revises: 20261017_reminder_completed_at
Create Date: 2026-10-17
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20261017_notification_email_delivery"
down_revision: Union[str, None] = "20261017_reminder_completed_at"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "notifications",
        sa.Column("due_date", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "notifications",
        sa.Column("email_sent_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "notifications",
        sa.Column("email_claimed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_notifications_email_claimed_at",
        "notifications",
        ["email_claimed_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_notifications_email_claimed_at", table_name="notifications")
    op.drop_column("notifications", "email_claimed_at")
    op.drop_column("notifications", "email_sent_at")
    op.drop_column("notifications", "due_date")
