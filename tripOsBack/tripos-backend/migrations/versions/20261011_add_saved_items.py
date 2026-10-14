"""Add saved destination and Wikipedia items.

Revision ID: 20261011_saved_items
Revises: 20261011_place_image
Create Date: 2026-10-11
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20261011_saved_items"
down_revision: Union[str, None] = "20261011_place_image"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "saved_items",
        sa.Column("id", sa.BigInteger().with_variant(sa.Integer, "sqlite"), primary_key=True),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("item_type", sa.String(length=30), nullable=False),
        sa.Column("item_key", sa.String(length=255), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("image", sa.String(length=500), nullable=True),
        sa.Column("location", sa.Text(), nullable=True),
        sa.Column("source_url", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.UniqueConstraint(
            "user_id",
            "item_type",
            "item_key",
            name="uq_saved_item_user_type_key",
        ),
    )
    op.create_index("ix_saved_items_id", "saved_items", ["id"])
    op.create_index("ix_saved_items_user_id", "saved_items", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_saved_items_user_id", table_name="saved_items")
    op.drop_index("ix_saved_items_id", table_name="saved_items")
    op.drop_table("saved_items")
