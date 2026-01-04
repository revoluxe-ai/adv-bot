"""Add user to balance reminder unique constraint

Revision ID: 1d7c5f8b9a2c
Revises: 0a8250e5cba3
Create Date: 2026-01-04 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "1d7c5f8b9a2c"
down_revision: Union[str, None] = "0a8250e5cba3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint(
        "uq_balance_reminders",
        "balancereminder",
        type_="unique",
    )
    op.create_unique_constraint(
        "uq_balance_reminders",
        "balancereminder",
        ["wb_cabinet_id", "user_id", "day", "level"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_balance_reminders",
        "balancereminder",
        type_="unique",
    )
    op.create_unique_constraint(
        "uq_balance_reminders",
        "balancereminder",
        ["wb_cabinet_id", "day", "level"],
    )

