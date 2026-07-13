"""Merge card ab hold heads

Revision ID: b8c4ac80176c
Revises: 6d3ef9bb7a12, c7d8e9f0a1b2
Create Date: 2026-07-14 00:44:41.381236

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b8c4ac80176c'
down_revision: Union[str, None] = ('6d3ef9bb7a12', 'c7d8e9f0a1b2')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
