"""Add profile avatars to users.

Revision ID: 20261015_user_avatar
Revises: 20261014_content_reports
Create Date: 2026-10-15
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20261015_user_avatar"
down_revision: Union[str, None] = "20261014_content_reports"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("avatar_filename", sa.String(length=40), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "avatar_filename")
