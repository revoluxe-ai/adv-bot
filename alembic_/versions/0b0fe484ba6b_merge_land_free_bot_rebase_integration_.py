"""merge land-free-bot-rebase integration heads

Объединяет topology-merge 8c541a39b7e2 и shelf-exhausted SoT e8f9a0b1c2d3
без дополнительных schema/data операций (land-free-bot-rebase integration).

Revision ID: 0b0fe484ba6b
Revises: 8c541a39b7e2, e8f9a0b1c2d3
Create Date: 2026-08-24 08:45:31.727133
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0b0fe484ba6b'
down_revision: Union[str, None] = ('8c541a39b7e2', 'e8f9a0b1c2d3')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Только topology merge — без schema/data изменений."""


def downgrade() -> None:
    """Только topology merge — без schema/data изменений."""
