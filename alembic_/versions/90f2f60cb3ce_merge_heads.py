"""merge heads

Revision ID: 90f2f60cb3ce
Revises: 7ca050e2bd76, a1b2c3d4e5f7
Create Date: 2026-03-03 22:54:33.197934

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '90f2f60cb3ce'
down_revision: Union[str, None] = ('7ca050e2bd76', 'a1b2c3d4e5f7')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
