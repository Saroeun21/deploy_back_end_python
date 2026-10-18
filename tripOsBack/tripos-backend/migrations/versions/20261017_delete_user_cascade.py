"""Allow destination catalog entries to outlive their creator account.

Revision ID: 20261017_delete_user_cascade
Revises: 20261016_google_avatar_url
Create Date: 2026-10-17
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20261017_delete_user_cascade"
down_revision: Union[str, None] = "20261016_reminder_email_delivery"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("destinations") as batch_op:
        batch_op.alter_column(
            "user_id",
            existing_type=sa.Integer(),
            nullable=True,
        )


def downgrade() -> None:
    connection = op.get_bind()
    unowned_destinations = connection.execute(
        sa.text("SELECT COUNT(*) FROM destinations WHERE user_id IS NULL")
    ).scalar_one()
    if unowned_destinations:
        raise RuntimeError(
            "Cannot restore NOT NULL on destinations.user_id while "
            "unowned catalog entries exist."
        )

    with op.batch_alter_table("destinations") as batch_op:
        batch_op.alter_column(
            "user_id",
            existing_type=sa.Integer(),
            nullable=False,
        )
