"""Fix target_place defaults and remove server_default

Revision ID: 4e513b70c164
Revises: c336752b29b2
Create Date: 2026-02-16 21:54:45.981602

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4e513b70c164'
down_revision: Union[str, None] = 'c336752b29b2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Remove server_default so new rows get NULL (matches ORM default=None).
    # Existing data is not changed.
    op.alter_column(
        "keywordsetting",
        "target_place",
        existing_type=sa.INTEGER(),
        nullable=True,
        server_default=None,
    )


def downgrade() -> None:
    op.alter_column(
        "keywordsetting",
        "target_place",
        existing_type=sa.INTEGER(),
        nullable=True,
        server_default=sa.text("2"),
    )
