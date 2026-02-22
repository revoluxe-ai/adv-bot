"""Add REPLACE_ON_TRIM to whitelistmode enum.

Revision ID: 9e2c4b71d2a1
Revises: cb757404243f
Create Date: 2026-02-21 12:00:00.000000
"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "9e2c4b71d2a1"
down_revision: Union[str, None] = "cb757404243f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE whitelistmode ADD VALUE IF NOT EXISTS 'REPLACE_ON_TRIM'")


def downgrade() -> None:
    # PostgreSQL does not support dropping enum values safely in-place.
    pass
