"""Add OLD_USER to passed_gate_reason enum

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-02-05

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ALTER TYPE ... ADD VALUE must run outside a transaction (PostgreSQL).
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE passedgatereason ADD VALUE IF NOT EXISTS 'OLD_USER'")


def downgrade() -> None:
    # PostgreSQL does not support removing values from an enum.
    # Reverting would require recreating the type and column; not implemented.
    pass
