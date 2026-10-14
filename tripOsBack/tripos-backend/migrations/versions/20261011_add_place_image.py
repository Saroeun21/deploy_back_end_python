"""Add image URLs to places.

Revision ID: 20261011_place_image
Revises: 20261002_trip_data
Create Date: 2026-10-11
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20261011_place_image"
down_revision: Union[str, None] = "20261002_trip_data"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("places", sa.Column("image", sa.String(length=500), nullable=True))


def downgrade() -> None:
    op.drop_column("places", "image")
