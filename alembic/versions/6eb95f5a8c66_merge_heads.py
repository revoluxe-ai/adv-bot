"""Merge heads

Revision ID: 6eb95f5a8c66
Revises: a689d49164e5, f8e1d9c2a3b4
Create Date: 2025-10-15 08:49:06.845867

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6eb95f5a8c66'
down_revision: Union[str, None] = ('a689d49164e5', 'f8e1d9c2a3b4')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
