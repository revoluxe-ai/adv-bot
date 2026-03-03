"""Add balance_went_negative_at to WBCabinet

Revision ID: a1b2c3d4e5f7
Revises: 58409c52364f
Create Date: 2026-03-03

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a1b2c3d4e5f7"
down_revision: Union[str, None] = "58409c52364f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "wbcabinet",
        sa.Column(
            "balance_went_negative_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("wbcabinet", "balance_went_negative_at")
