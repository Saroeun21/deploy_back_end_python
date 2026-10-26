"""Use SQLite-compatible autoincrementing itinerary primary keys.

Revision ID: 20261016_itin_autoinc
Revises: 20261015_user_avatar
Create Date: 2026-10-16
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20261016_itin_autoinc"
down_revision: Union[str, None] = "20261015_user_avatar"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _alter_sqlite_primary_key_types(target_type: sa.types.TypeEngine) -> None:
    bind = op.get_bind()
    if bind.dialect.name != "sqlite":
        return

    for table in ("itinerary_days", "itinerary_items"):
        with op.batch_alter_table(table) as batch_op:
            batch_op.alter_column(
                "id",
                existing_type=sa.BigInteger(),
                type_=target_type,
                existing_nullable=False,
            )


def upgrade() -> None:
    _alter_sqlite_primary_key_types(sa.Integer())


def downgrade() -> None:
    _alter_sqlite_primary_key_types(sa.BigInteger())
