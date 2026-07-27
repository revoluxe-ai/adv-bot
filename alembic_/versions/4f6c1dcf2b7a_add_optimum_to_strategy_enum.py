"""Add OPTIMUM to strategy enum

Revision ID: 4f6c1dcf2b7a
Revises: 92bdd3917621
Create Date: 2026-06-23 21:23:39.131754

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "4f6c1dcf2b7a"
down_revision: Union[str, None] = "92bdd3917621"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE strategy ADD VALUE IF NOT EXISTS 'OPTIMUM';")


def downgrade() -> None:
    # PostgreSQL does not support removing enum values safely without rebuilding the type.
    pass
