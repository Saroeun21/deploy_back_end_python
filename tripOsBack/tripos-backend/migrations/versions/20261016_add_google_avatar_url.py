"""Store Google account avatar URLs.

Revision ID: 20261016_google_avatar_url
Revises: 20261016_itin_autoinc
Create Date: 2026-10-16
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20261016_google_avatar_url"
down_revision: Union[str, None] = "20261016_itin_autoinc"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("google_avatar_url", sa.String(length=2048), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "google_avatar_url")
