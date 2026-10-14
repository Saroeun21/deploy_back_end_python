"""Add USD admission and visit cost estimates.

Revision ID: 20261011_usd_costs
Revises: 20261011_saved_items
Create Date: 2026-10-11
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20261011_usd_costs"
down_revision: Union[str, None] = "20261011_saved_items"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "destinations",
        sa.Column("average_daily_cost_usd", sa.Numeric(10, 2), nullable=True),
    )
    op.add_column(
        "places",
        sa.Column("admission_fee_usd", sa.Numeric(10, 2), nullable=True),
    )
    op.add_column(
        "places",
        sa.Column("estimated_visit_cost_usd", sa.Numeric(10, 2), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("places", "estimated_visit_cost_usd")
    op.drop_column("places", "admission_fee_usd")
    op.drop_column("destinations", "average_daily_cost_usd")
